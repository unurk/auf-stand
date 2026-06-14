"""Rückkanal: Beantwortet Telegram-Fragen auf Basis aktueller Presse-Artikel."""
from __future__ import annotations

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

        # Nur Text-Nachrichten von bekannten Chat-IDs beantworten
        if not text or chat_id not in allowed_ids or text.startswith("/"):
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

    # Per-Artikel-Feedback: artfb|datum|edition|idx|rating
    if parts[0] == "artfb" and len(parts) == 5:
        _, datum, edition, idx_str, rating = parts
        try:
            article_idx = int(idx_str)
        except ValueError:
            tg.answer_callback(cq.get("id", ""))
            return 0
        state_module.record_article_feedback(current_state, datum, edition, article_idx, rating, chat_id)
        tg.answer_callback(cq.get("id", ""), "Notiert ✓")
        print(f"Artikel-Feedback: {edition} Artikel {article_idx} {'👍' if rating == 'up' else '👎'}")
        return 1

    # Ausgaben-Feedback: fb|datum|edition|rating
    if len(parts) != 4 or parts[0] != "fb":
        tg.answer_callback(cq.get("id", ""))
        return 0

    _, datum, edition, rating = parts
    state_module.record_feedback(current_state, datum, edition, rating, chat_id)
    tg.answer_callback(cq.get("id", ""))
    message_id = msg.get("message_id")
    if message_id is not None:
        mark = "👍" if rating == "up" else "👎"
        tg.confirm_feedback(chat_id, message_id, f"Danke — notiert {mark} ✓")
    print(f"Feedback notiert: {edition} {'👍' if rating == 'up' else '👎'}")
    return 1
