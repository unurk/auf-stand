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
        # **bold** inline
        line = re.sub(r"\*\*(.+?)\*\*", lambda m: f"*{_escape(m.group(1))}*", line)
        # *italic* inline (nur wenn nicht schon fett verarbeitet)
        line = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", lambda m: f"_{_escape(m.group(1))}_", line)
        # Restliche Sonderzeichen escapen (außer was schon verarbeitet)
        line = _escape_remaining(line)
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


def send_telegram(markdown: str, chat_ids: list[str]) -> None:
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
        for chunk in _split(text):
            resp = httpx.post(url, json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "MarkdownV2",
            }, timeout=15)
            if resp.status_code != 200:
                data = resp.json()
                print(f"Telegram-Fehler ({chat_id}): {data.get('description', resp.text)}")
                break
        else:
            print(f"Telegram: gesendet an {chat_id}")


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
