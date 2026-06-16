"""Vorausschau: Termine der nächsten Tage, gefiltert auf Themen-Tracker."""
from __future__ import annotations

from datetime import date

WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS = [
    "Jän", "Feb", "Mär", "Apr", "Mai", "Jun",
    "Jul", "Aug", "Sep", "Okt", "Nov", "Dez",
]


def get_upcoming(termine: list[dict], days_ahead: int = 6) -> list[dict]:
    today = date.today()
    result = []
    for t in termine:
        try:
            event_date = date.fromisoformat(str(t["datum"]))
        except (KeyError, ValueError):
            continue
        delta = (event_date - today).days
        if 0 <= delta <= days_ahead:
            result.append({**t, "delta_days": delta, "date_obj": event_date})
    return sorted(result, key=lambda x: x["date_obj"])


def format_vorausschau(termine: list[dict]) -> str:
    """Gibt einen Markdown-Block mit kommenden Terminen zurück, oder ''."""
    upcoming = get_upcoming(termine)
    if not upcoming:
        return ""
    lines = ["## 📅 Diese Woche noch"]
    for t in upcoming:
        d = t["date_obj"]
        label = f"{WEEKDAYS[d.weekday()]} {d.day}. {MONTHS[d.month - 1]}."
        name = t.get("name", "")
        tracker = t.get("tracker", "")
        hint = (' — betrifft Tracker „' + tracker + '“') if tracker else ""
        lines.append(f"- **{label}** · {name}{hint}")
    return "\n".join(lines)
