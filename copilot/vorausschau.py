"""Vorausschau: Termine der nächsten Tage, gefiltert auf Themen-Tracker."""
from __future__ import annotations

from datetime import date

from . import i18n


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


def format_vorausschau(termine: list[dict], lang: str = "de") -> str:
    """Gibt einen Markdown-Block mit kommenden Terminen zurück, oder ''."""
    upcoming = get_upcoming(termine)
    if not upcoming:
        return ""
    weekdays = i18n.t(lang, "weekdays_short")
    months = i18n.t(lang, "months_short")
    lines = [i18n.t(lang, "vorausschau_heading")]
    for t in upcoming:
        d = t["date_obj"]
        label = i18n.t(lang, "vorausschau_date_fmt").format(
            weekday=weekdays[d.weekday()], day=d.day, month=months[d.month - 1]
        )
        name = t.get("name", "")
        tracker = t.get("tracker", "")
        hint = i18n.t(lang, "vorausschau_tracker_fmt").format(tracker=tracker) if tracker else ""
        lines.append(f"- **{label}** · {name}{hint}")
    return "\n".join(lines)
