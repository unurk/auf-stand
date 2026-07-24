"""Versand des Lagebilds via Telegram Bot API."""
from __future__ import annotations

import os
import re

import httpx


def _to_telegram_md(markdown: str) -> str:
    """Konvertiert das Lagebild-Markdown in Telegram MarkdownV2."""
    lines: list[str] = []
    for raw in markdown.splitlines():
        line = raw.rstrip()
        # Trennlinie
        if line.startswith("---"):
            lines.append("—————————————")
            continue
        # H1 → fett + Großschreibung beibehalten
        if line.startswith("# "):
            text = _escape(line[2:])
            lines.append(f"*{text}*")
            continue
        # H2 → fett
        if line.startswith("## "):
            text = _escape(line[3:])
            lines.append(f"*{text}*")
            continue
        # Links und Bold-Spans vor dem Escapen als Platzhalter sichern, damit
        # die Italic-Regex und _escape_remaining sie nicht versehentlich verändern.
        _placeholders: dict[str, str] = {}

        def _replace_link(m: re.Match) -> str:
            key = f"\x00L{len(_placeholders)}\x00"
            link_text = _escape(m.group(1))
            link_url = m.group(2).replace("\\", "\\\\").replace(")", "\\)")
            _placeholders[key] = f"[{link_text}]({link_url})"
            return key

        def _replace_bold(m: re.Match) -> str:
            key = f"\x00B{len(_placeholders)}\x00"
            _placeholders[key] = f"*{_escape(m.group(1))}*"
            return key

        line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _replace_link, line)
        line = re.sub(r"\*\*(.+?)\*\*", _replace_bold, line)
        # *italic* inline (nach Bold, damit Bold-Output nicht erneut gematcht wird)
        line = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", lambda m: f"_{_escape(m.group(1))}_", line)
        # Restliche Sonderzeichen escapen (außer was schon verarbeitet)
        line = _escape_remaining(line)
        # Platzhalter durch fertige Telegram-Tokens ersetzen
        for key, value in _placeholders.items():
            line = line.replace(key, value)
        lines.append(line)
    return "\n".join(lines)


_SPECIAL = r"\_[]()~`>#+-=|{}.!"


def _escape(text: str) -> str:
    """Escapt alle Telegram MarkdownV2-Sonderzeichen."""
    for ch in _SPECIAL:
        text = text.replace(ch, f"\\{ch}")
    return text


def _escape_remaining(text: str) -> str:
    """Escapt Sonderzeichen außerhalb bereits gesetzter Markdown-Tokens."""
    result = []
    i = 0
    while i < len(text):
        # Bereits gesetzte Token (*…*, _…_) unverändert lassen
        if text[i] in ("*", "_") and i + 1 < len(text):
            end = text.find(text[i], i + 1)
            if end != -1:
                result.append(text[i : end + 1])
                i = end + 1
                continue
        if text[i] in _SPECIAL:
            result.append(f"\\{text[i]}")
        else:
            result.append(text[i])
        i += 1
    return "".join(result)


def telegram_configured() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN"))


def send_photo(path, caption: str, chat_ids: list[str]) -> None:
    """Schickt ein Bild mit Bildunterschrift (Klartext, kein Markdown)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token or not chat_ids:
        print("Telegram nicht konfiguriert — Foto-Versand übersprungen.")
        return
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    for chat_id in chat_ids:
        with open(path, "rb") as fh:
            resp = httpx.post(
                url,
                data={"chat_id": chat_id, "caption": caption},
                files={"photo": fh},
                timeout=30,
            )
        if resp.status_code == 200:
            print(f"Telegram: Foto gesendet an {chat_id}")
        else:
            print(f"Telegram-Fehler ({chat_id}): {resp.json().get('description', resp.text)}")


def send_audio(path, caption: str, chat_ids: list[str], title: str | None = None) -> None:
    """Schickt eine mp3 als abspielbare Audio-Nachricht (Klartext-Caption)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token or not chat_ids:
        print("Telegram nicht konfiguriert — Audio-Versand übersprungen.")
        return
    url = f"https://api.telegram.org/bot{token}/sendAudio"
    data = {"chat_id": "", "caption": caption, "performer": "Die Presse · Copilot"}
    if title:
        data["title"] = title
    for chat_id in chat_ids:
        data["chat_id"] = chat_id
        try:
            with open(path, "rb") as fh:
                resp = httpx.post(url, data=data, files={"audio": fh}, timeout=60)
        except Exception as exc:
            print(f"Telegram-Audio-Fehler ({chat_id}): {exc}")
            continue
        if resp.status_code == 200:
            print(f"Telegram: Audio gesendet an {chat_id}")
        else:
            print(f"Telegram-Fehler ({chat_id}): {resp.json().get('description', resp.text)}")


def send_alert(text: str, chat_ids: list[str]) -> None:
    """Schickt eine Warnung als einfache Textnachricht (ohne Markdown-Formatierung)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token or not chat_ids:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chat_id in chat_ids:
        try:
            httpx.post(url, json={"chat_id": chat_id, "text": text}, timeout=15)
        except Exception:
            pass  # Eine fehlgeschlagene Warnung darf den Lauf nicht stoppen


def _feedback_keyboard(feedback_key: str, article_headings: list[str] | None = None) -> dict:
    """Inline-Tastatur: optional 👍/👎 pro Artikel, danach Ausgaben-Gesamtbewertung.

    Die letzte Zeile trägt die beiden Signale, die das Produkt bisher nicht hatte:
    „gelesen" (misst die Leserin statt unseren Cron) und „hat was gefehlt"
    (Fehler zweiter Art — die einzige Fehlerklasse, die ein Auswahl-Prompt aus
    sich heraus nie korrigieren kann).
    """
    rows = []
    if article_headings:
        datum_edition = feedback_key  # Format: "YYYY-MM-DD|edition"
        for i, heading in enumerate(article_headings):
            label = heading[:22] + "…" if len(heading) > 22 else heading
            rows.append([
                {"text": f"👍 {label}", "callback_data": f"artfb|{datum_edition}|{i}|up"},
                {"text": "👎", "callback_data": f"artfb|{datum_edition}|{i}|down"},
            ])
    rows.append([
        {"text": "👍 Ausgabe", "callback_data": f"fb|{feedback_key}|up"},
        {"text": "👎 Ausgabe", "callback_data": f"fb|{feedback_key}|down"},
    ])
    rows.append([
        {"text": "✓ Gelesen", "callback_data": f"read|{feedback_key}"},
        {"text": "🔍 Hat was gefehlt?", "callback_data": f"fehlt|{feedback_key}"},
    ])
    return {"inline_keyboard": rows}


def profil_keyboard(frage: dict) -> dict:
    """Tastatur für eine Profil-Frage: je Option ein Knopf (prof|key|wert)."""
    return {
        "inline_keyboard": [
            [{"text": label, "callback_data": f"prof|{frage['key']}|{wert}"}]
            for wert, label, _satz in frage["optionen"]
        ]
    }


def send_question(text: str, chat_id: str, keyboard: dict) -> None:
    """Schickt eine Frage mit Antwort-Knöpfen (Klartext, kein Markdown)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        httpx.post(
            url,
            json={"chat_id": chat_id, "text": text, "reply_markup": keyboard},
            timeout=15,
        )
    except Exception as exc:
        print(f"Telegram-Frage-Fehler ({chat_id}): {exc}")


def send_quiz(frage: str, optionen: list[str], richtig: int, chat_ids: list[str],
              erklaerung: str = "") -> bool:
    """Schickt eine Quizfrage als natives Telegram-Quiz. True bei Erfolg.

    Wirkungsmessung statt Zustellmessung: ob jemand informiert IST, zeigt sich
    nur an der Antwort — nicht daran, dass wir geliefert haben.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token or not chat_ids:
        print("Telegram nicht konfiguriert — Quiz übersprungen.")
        return False
    url = f"https://api.telegram.org/bot{token}/sendPoll"
    ok = False
    for chat_id in chat_ids:
        payload = {
            "chat_id": chat_id,
            "question": frage[:300],
            "options": [o[:100] for o in optionen[:10]],
            "type": "quiz",
            "correct_option_id": richtig,
            "is_anonymous": False,
        }
        if erklaerung:
            payload["explanation"] = erklaerung[:200]
        try:
            resp = httpx.post(url, json=payload, timeout=15)
        except Exception as exc:
            print(f"Telegram-Quiz-Fehler ({chat_id}): {exc}")
            continue
        if resp.status_code == 200:
            ok = True
        else:
            print(f"Telegram-Quiz-Fehler ({chat_id}): {resp.text[:200]}")
    return ok


def send_telegram(
    markdown: str,
    chat_ids: list[str],
    feedback_key: str | None = None,
    article_headings: list[str] | None = None,
) -> None:
    if not chat_ids:
        print("Keine Telegram-Chat-IDs in config.yaml — Versand übersprungen.")
        return
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("TELEGRAM_BOT_TOKEN nicht in .env — Versand übersprungen.")
        return

    text = _to_telegram_md(markdown)
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    for chat_id in chat_ids:
        chunks = _split(text)
        for i, chunk in enumerate(chunks):
            payload = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "MarkdownV2",
            }
            # Bewertungs-Buttons nur an den letzten Chunk hängen.
            if feedback_key and i == len(chunks) - 1:
                payload["reply_markup"] = _feedback_keyboard(feedback_key, article_headings)
            resp = httpx.post(url, json=payload, timeout=15)
            if resp.status_code != 200:
                data = resp.json()
                print(f"Telegram-Fehler ({chat_id}): {data.get('description', resp.text)}")
                break
        else:
            print(f"Telegram: gesendet an {chat_id}")


def answer_callback(callback_query_id: str, text: str = "Danke ✓") -> None:
    """Quittiert einen Button-Tap (stoppt den Lade-Spinner im Client)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return
    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    try:
        httpx.post(url, json={"callback_query_id": callback_query_id, "text": text}, timeout=15)
    except Exception:
        pass  # Eine fehlgeschlagene Quittung darf den Lauf nicht stoppen


def confirm_feedback(chat_id: str, message_id: int, text: str) -> None:
    """Ersetzt die 👍/👎-Tastatur durch eine Bestätigung — Nachrichtentext bleibt."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return
    url = f"https://api.telegram.org/bot{token}/editMessageReplyMarkup"
    keyboard = {"inline_keyboard": [[{"text": text, "callback_data": "fb|done"}]]}
    try:
        httpx.post(
            url,
            json={"chat_id": chat_id, "message_id": message_id, "reply_markup": keyboard},
            timeout=15,
        )
    except Exception:
        pass


def _split(text: str, limit: int = 4000) -> list[str]:
    """Teilt langen Text an Absatzgrenzen auf, max. `limit` Zeichen pro Teil."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for para in text.split("\n\n"):
        para_len = len(para) + 2
        if current_len + para_len > limit and current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += para_len
    if current:
        chunks.append("\n\n".join(current))
    return chunks
