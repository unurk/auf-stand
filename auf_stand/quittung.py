"""Wochen-Quittung: macht den Wert des Lagebilds einmal pro Woche sichtbar."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import state as state_module, telegram

LESETEMPO_WOERTER_PRO_MINUTE = 200


def build_quittung(state: dict) -> str | None:
    """Baut die Wochen-Quittung aus den Statistiken der letzten 7 Tage."""
    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat()
    week = [s for s in state.get("stats", []) if s["date"] >= cutoff]
    if not week:
        return None

    editions = len(week)
    points = sum(s["points"] for s in week)
    words = sum(s["words"] for s in week)
    articles = sum(s["new_articles"] for s in week)
    days_on_stand = len({s["date"] for s in week})
    minutes = max(1, round(words / LESETEMPO_WOERTER_PRO_MINUTE))

    return (
        "# 📬 Deine Wochen-Quittung\n"
        "\n"
        f"Diese Woche sind **{articles} Artikel** in deinen Quellen erschienen.\n"
        "\n"
        f"Du hast die **{points} wichtigsten Entwicklungen** daraus erfasst — "
        f"in {editions} {'Lagebild' if editions == 1 else 'Lagebildern'}, "
        f"Gesamtlesezeit ca. **{minutes} {'Minute' if minutes == 1 else 'Minuten'}**.\n"
        "\n"
        f"✅ Du warst **{days_on_stand}/7 Tagen auf Stand.**\n"
        "\n"
        "---\n"
        "*Nächstes Lagebild: morgen 7:00.*"
    )


def cmd_woche(config: dict) -> int:
    current_state = state_module.load_state()
    quittung = build_quittung(current_state)
    if quittung is None:
        print("Keine Statistiken der letzten 7 Tage — keine Quittung.")
        return 0
    telegram.send_telegram(quittung, config.get("telegram_chat_ids", []))
    try:
        print(quittung)
    except UnicodeEncodeError:
        # Windows-Konsole (cp1252) kann manche Emojis nicht darstellen
        print(quittung.encode("ascii", "ignore").decode())
    return 0
