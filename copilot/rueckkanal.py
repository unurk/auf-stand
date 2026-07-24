"""Rückkanal: Beantwortet Telegram-Fragen auf Basis aktueller Presse-Artikel."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import httpx

BASE_DIR = Path(__file__).resolve().parent.parent
OFFSET_FILE = BASE_DIR / "data" / "rueckkanal_offset.json"
PROMPT_PATH = BASE_DIR / "prompts" / "rueckkanal.md"


def _load_offset() -> int:
    if OFFSET_FILE.exists():
        return json.loads(OFFSET_FILE.read_text(encoding="utf-8")).get("offset", 0)
    return 0


def _save_offset(offset: int) -> None:
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(json.dumps({"offset": offset}), encoding="utf-8")


def _get_updates(token: str, offset: int) -> list[dict]:
    try:
        resp = httpx.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": offset, "timeout": 0, "limit": 20},
            timeout=12,
        )
        if resp.status_code == 200:
            return resp.json().get("result", [])
    except Exception as exc:
        print(f"Telegram getUpdates Fehler: {exc}")
    return []


def _build_prompt(question: str, articles: list) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    lines = [template.replace("{FRAGE}", question), "\n\n---\n\n# Artikel\n"]
    for article in articles[:15]:
        published = (
            article.published.strftime("%d.%m. %H:%M") if article.published else "ohne Datum"
        )
        link = f"\n  Link: {article.link}" if article.link else ""
        lines.append(
            f"- [{article.ressort}] {article.title} ({published})\n  {article.teaser}{link}"
        )
    return "\n".join(lines)


def cmd_rueckkanal(config: dict) -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("TELEGRAM_BOT_TOKEN fehlt — Rückkanal übersprungen.")
        return 0

    allowed_ids = {str(cid) for cid in config.get("telegram_chat_ids", [])}
    offset = _load_offset()
    updates = _get_updates(token, offset)

    if not updates:
        print("Keine neuen Nachrichten.")
        return 0

    from .fetch import fetch_all, filter_recent
    from . import state as state_module, synthesize, telegram as tg

    current_state = state_module.load_state()
    articles: list | None = None  # erst bei Bedarf laden (spart einen Fetch)
    processed = 0
    feedback_count = 0

    for update in updates:
        update_id = update["update_id"]
        offset = max(offset, update_id + 1)

        # Button-Tap (Relevanz-Bewertung) — kommt über denselben Poll.
        cq = update.get("callback_query")
        if cq:
            feedback_count += _handle_callback(cq, allowed_ids, current_state, tg)
            continue

        msg = update.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id", ""))
        text = msg.get("text", "").strip()

        if not text or chat_id not in allowed_ids:
            continue

        # /themen EZB Miet Börse — speichert Themen-Präferenzen
        if text.startswith("/themen"):
            from . import synthesize as syn
            parts = text[7:].strip().split()
            all_topics = config.get("topics", [])
            matched = [
                syn.topic_name(t) for t in all_topics
                if syn.topic_keyword(t).lower() in [p.lower() for p in parts]
            ]
            state_module.save_user_topic_prefs(current_state, matched)
            state_module.save_state(current_state)
            names = ", ".join(matched) if matched else "keine"
            tg.send_alert(f"✅ Themen gespeichert: {names}", [chat_id])
            print(f"Themen-Präferenzen gesetzt: {names}")
            continue

        # /thema-neu Name|Schlagwort — eigenes Thema hinzufügen
        if text.startswith("/thema-neu"):
            payload = text[10:].strip()
            if "|" in payload:
                name, kw = payload.split("|", 1)
                name, kw = name.strip(), kw.strip()
                custom = current_state.setdefault("custom_topics", [])
                if not any(c.get("schlagwort", "").lower() == kw.lower() for c in custom):
                    custom.append({"name": name, "schlagwort": kw})
                    state_module.save_state(current_state)
                    tg.send_alert(f"✅ Thema hinzugefügt: {name} (#{kw})", [chat_id])
                    print(f"Eigenes Thema hinzugefügt: {name}|{kw}")
                else:
                    tg.send_alert(f"ℹ️ Schlagwort #{kw} existiert bereits.", [chat_id])
            else:
                tg.send_alert("Format: /thema-neu Name|Schlagwort", [chat_id])
            continue

        # /profil — Wirkungs-Profil setzen (Fragen mit Knöpfen), importieren
        # (base64-Code aus der PWA) oder löschen.
        if text.startswith("/profil"):
            from . import profil as profil_mod
            payload = text[7:].strip()
            if payload in ("loeschen", "löschen", "reset"):
                profil_mod.profil_loeschen(current_state)
                state_module.save_state(current_state)
                tg.send_alert("✅ Wirkungs-Profil gelöscht.", [chat_id])
                continue
            if payload:
                try:
                    n = profil_mod.code_uebernehmen(current_state, payload)
                except Exception as exc:
                    print(f"Profil-Code ungültig: {exc}")
                    tg.send_alert("❌ Profil-Code ungültig. Bitte in der App neu erzeugen.", [chat_id])
                    continue
                if n:
                    state_module.save_state(current_state)
                    antworten = profil_mod.get_profil(current_state)
                    tg.send_alert(
                        f"✅ Profil übernommen ({n} Angaben): "
                        f"{profil_mod.kurzfassung(antworten)}",
                        [chat_id],
                    )
                else:
                    tg.send_alert("❌ Profil-Code enthielt keine gültigen Angaben.", [chat_id])
                continue
            _frage_stellen(current_state, chat_id, tg)
            continue

        # /fehlt <Thema> — was aus Sicht der Leserin gefehlt hat (Fehler 2. Art)
        if text.startswith("/fehlt"):
            fehlt = text[6:].strip()
            if not fehlt:
                tg.send_alert(
                    "Was hat gefehlt? Format: /fehlt <Thema oder Schlagzeile>", [chat_id]
                )
                continue
            state_module.record_missing_feedback(current_state, fehlt, chat_id)
            state_module.save_state(current_state)
            tg.send_alert(
                "✅ Notiert — das fließt in die Auswahl der nächsten Ausgaben ein.",
                [chat_id],
            )
            print(f"Fehlend gemeldet: {fehlt[:80]}")
            continue

        # /gelesen — manuelles Lese-Signal (z. B. nach der Audio-Version)
        if text.startswith("/gelesen"):
            state_module.record_read(current_state, "befehl")
            state_module.save_state(current_state)
            tage = state_module.read_streak(current_state)
            tg.send_alert(f"✅ Notiert — {tage}. Tag in Folge informiert.", [chat_id])
            continue

        # /push <base64-blob> — Web-Push-Subscription aus der PWA registrieren
        if text.startswith("/push"):
            payload = text[5:].strip()
            try:
                pad = "=" * (-len(payload) % 4)
                sub = json.loads(base64.urlsafe_b64decode(payload + pad))
                state_module.add_push_subscription(current_state, sub)
                state_module.save_state(current_state)
                tg.send_alert("✅ Push-Benachrichtigungen aktiviert.", [chat_id])
                print(f"Push-Abo registriert ({chat_id}).")
            except Exception as exc:
                print(f"Push-Code ungültig: {exc}")
                tg.send_alert("❌ Push-Code ungültig. Bitte in der App neu erzeugen.", [chat_id])
            continue

        # Andere Slash-Befehle ignorieren
        if text.startswith("/"):
            continue

        if articles is None:
            articles = filter_recent(fetch_all(config).articles, 24)

        print(f"Frage ({chat_id}): {text[:100]}")
        try:
            prompt = _build_prompt(text, articles)
            answer = synthesize.synthesize(prompt, config)
            tg.send_telegram(answer, [chat_id])
            processed += 1
        except Exception as exc:
            print(f"Fehler bei Antwort: {exc}")
            tg.send_alert(f"❌ Rückkanal: Antwort fehlgeschlagen — {exc}", [chat_id])

    _save_offset(offset)
    if feedback_count:
        state_module.save_state(current_state)
    print(f"{processed} Frage(n) beantwortet, {feedback_count} Bewertung(en) notiert.")
    return 0


def _frage_stellen(current_state: dict, chat_id: str, tg) -> None:
    """Schickt die nächste offene Profil-Frage — oder die Zusammenfassung."""
    from . import profil as profil_mod

    antworten = profil_mod.get_profil(current_state)
    frage = profil_mod.naechste_frage(antworten)
    if frage is None:
        tg.send_alert(
            "✅ Dein Wirkungs-Profil steht: "
            f"{profil_mod.kurzfassung(antworten)}\n\n"
            "Damit wird „Warum es zählt“ konkret statt allgemein. "
            "Ändern: /profil loeschen und neu starten.",
            [chat_id],
        )
        return
    beantwortet, gesamt = profil_mod.fortschritt(antworten)
    tg.send_question(
        f"Frage {beantwortet + 1} von {gesamt}: {frage['frage']}",
        chat_id,
        tg.profil_keyboard(frage),
    )


def _handle_callback(cq: dict, allowed_ids: set[str], current_state: dict, tg) -> int:
    """Verarbeitet einen Button-Tap. Gibt 1 zurück, wenn Feedback notiert wurde."""
    from . import state as state_module

    data = cq.get("data", "")
    msg = cq.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    parts = data.split("|")

    if chat_id not in allowed_ids:
        tg.answer_callback(cq.get("id", ""))
        return 0

    # Profil-Antwort: prof|key|wert
    if parts[0] == "prof" and len(parts) == 3:
        from . import profil as profil_mod
        if profil_mod.antwort_speichern(current_state, parts[1], parts[2]):
            tg.answer_callback(cq.get("id", ""), "Notiert ✓")
            _frage_stellen(current_state, chat_id, tg)
            return 1
        tg.answer_callback(cq.get("id", ""))
        return 0

    # Lese-Signal: read|datum|edition
    if parts[0] == "read" and len(parts) == 3:
        state_module.record_read(current_state, "telegram_tap", parts[1], parts[2])
        tage = state_module.read_streak(current_state)
        tg.answer_callback(cq.get("id", ""), f"Gelesen ✓ — {tage}. Tag in Folge")
        return 1

    # „Hat was gefehlt?": fehlt|datum|edition — erklärt den Befehl, notiert später
    if parts[0] == "fehlt":
        tg.answer_callback(cq.get("id", ""), "Sag uns was ✓")
        tg.send_alert(
            "Was hat gefehlt? Antworte mit:\n/fehlt <Thema oder Schlagzeile>\n\n"
            "Das ist die einzige Rückmeldung, die wir sonst nie bekommen — "
            "wir sehen nur, was drin war, nie was fehlte.",
            [chat_id],
        )
        return 0

    # Per-Artikel-Feedback: artfb|datum|edition|idx|rating
    if parts[0] == "artfb" and len(parts) == 5:
        _, datum, edition, idx_str, rating = parts
        try:
            article_idx = int(idx_str)
        except ValueError:
            tg.answer_callback(cq.get("id", ""))
            return 0
        state_module.record_article_feedback(current_state, datum, edition, article_idx, rating, chat_id)
        # Wer einzelne Punkte bewertet, hat die Ausgabe gelesen.
        state_module.record_read(current_state, "artfb", datum, edition)
        tg.answer_callback(cq.get("id", ""), "Notiert ✓")
        print(f"Artikel-Feedback: {edition} Artikel {article_idx} {'👍' if rating == 'up' else '👎'}")
        return 1

    # Ausgaben-Feedback: fb|datum|edition|rating
    if len(parts) != 4 or parts[0] != "fb":
        tg.answer_callback(cq.get("id", ""))
        return 0

    _, datum, edition, rating = parts
    state_module.record_feedback(current_state, datum, edition, rating, chat_id)
    state_module.record_read(current_state, "fb", datum, edition)
    tg.answer_callback(cq.get("id", ""))
    message_id = msg.get("message_id")
    if message_id is not None:
        mark = "👍" if rating == "up" else "👎"
        tg.confirm_feedback(chat_id, message_id, f"Danke — notiert {mark} ✓")
    print(f"Feedback notiert: {edition} {'👍' if rating == 'up' else '👎'}")
    return 1
