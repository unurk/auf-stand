"""Wochen-Quittung: macht den Wert des Lagebilds einmal pro Woche sichtbar — als Bild-Karte."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import state as state_module, telegram

OUT_DIR = Path(__file__).resolve().parent.parent / "out"
LESETEMPO_WOERTER_PRO_MINUTE = 200
WEEKDAY_LABELS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

# Presse-Optik (passend zum HTML-Template in render.py)
BG = "#f5f3ef"
INK = "#1a1a1a"
MUTED = "#8a8378"
ACCENT = "#b5543b"
GREEN = "#2e6b3f"
GREY = "#d8d2c6"


def week_stats(state: dict) -> dict | None:
    """Aggregiert die Statistiken der letzten 7 Tage. None wenn keine Daten."""
    today = datetime.now(timezone.utc).date()
    window = [today - timedelta(days=i) for i in range(6, -1, -1)]
    cutoff = window[0].isoformat()
    week = [s for s in state.get("stats", []) if s["date"] >= cutoff]
    if not week:
        return None

    active_dates = {s["date"] for s in week}
    days = [
        (WEEKDAY_LABELS[d.weekday()], d.isoformat() in active_dates)
        for d in window
    ]
    words = sum(s["words"] for s in week)
    return {
        "articles": sum(s["new_articles"] for s in week),
        "points": sum(s["points"] for s in week),
        "editions": len(week),
        "minutes": max(1, round(words / LESETEMPO_WOERTER_PRO_MINUTE)),
        "days": days,
        "days_on_stand": len(active_dates),
        "range_label": _range_label(window[0], today),
    }


def _range_label(start: date, end: date) -> str:
    months = ["Jän.", "Feb.", "März", "April", "Mai", "Juni",
              "Juli", "Aug.", "Sep.", "Okt.", "Nov.", "Dez."]
    return f"{start.day}. {months[start.month - 1]} – {end.day}. {months[end.month - 1]} {end.year}"


def build_image(stats: dict, path: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle

    fig = plt.figure(figsize=(10.8, 10.8), dpi=100)
    fig.patch.set_facecolor(BG)

    # Kopf
    fig.text(0.5, 0.93, "DIE PRESSE · AUF STAND", ha="center",
             fontsize=15, color=MUTED, family="sans-serif")
    fig.text(0.5, 0.855, "Deine Wochen-Quittung", ha="center",
             fontsize=44, color=INK, family="serif", weight="bold")
    fig.text(0.5, 0.81, stats["range_label"], ha="center",
             fontsize=17, color=MUTED, family="sans-serif")

    # Drei grosse Kennzahlen
    cols = [
        (0.21, f"{stats['articles']}", "Artikel\nerschienen", MUTED),
        (0.50, f"{stats['points']}", "Entwicklungen\nerfasst", ACCENT),
        (0.79, f"{stats['minutes']}", "Minuten\nLesezeit", MUTED),
    ]
    for x, number, label, color in cols:
        fig.text(x, 0.63, number, ha="center", fontsize=78,
                 color=color, family="serif", weight="bold")
        fig.text(x, 0.555, label, ha="center", va="top", fontsize=17,
                 color=MUTED, family="sans-serif", linespacing=1.4)

    # Wochenleiste mit Haken
    ax = fig.add_axes([0.1, 0.27, 0.8, 0.16])
    ax.set_xlim(-0.6, 6.6)
    ax.set_ylim(-1.4, 1.0)
    ax.set_aspect("equal")
    ax.axis("off")
    for i, (label, active) in enumerate(stats["days"]):
        face = GREEN if active else GREY
        ax.add_patch(Circle((i, 0.2), 0.36, facecolor=face, edgecolor="none"))
        if active:
            ax.text(i, 0.2, "✓", ha="center", va="center",
                    fontsize=26, color="white", weight="bold")
        ax.text(i, -0.85, label, ha="center", va="center",
                fontsize=15, color=MUTED, family="sans-serif")

    # Fazit
    fig.text(0.5, 0.175,
             f"Du warst {stats['days_on_stand']} von 7 Tagen auf Stand",
             ha="center", fontsize=24, color=GREEN, family="serif", weight="bold")
    fig.text(0.5, 0.115,
             f"Verdichtet aus {stats['articles']} Artikeln in {stats['editions']} "
             f"{'Lagebild' if stats['editions'] == 1 else 'Lagebildern'} — statt stundenlangem Scrollen.",
             ha="center", fontsize=15, color=MUTED, family="sans-serif")

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=BG, bbox_inches="tight", pad_inches=0.4)
    plt.close(fig)
    return path


def cmd_woche(config: dict) -> int:
    current_state = state_module.load_state()
    stats = week_stats(current_state)
    if stats is None:
        print("Keine Statistiken der letzten 7 Tage — keine Quittung.")
        return 0

    image = build_image(stats, OUT_DIR / "wochen-quittung.png")
    caption = (
        f"📬 Deine Wochen-Quittung: {stats['points']} Entwicklungen aus "
        f"{stats['articles']} Artikeln, in ca. {stats['minutes']} Minuten. "
        f"Du warst {stats['days_on_stand']}/7 Tagen auf Stand ✓"
    )
    telegram.send_photo(image, caption, config.get("telegram_chat_ids", []))
    print(f"Quittung erzeugt: {image}")
    return 0
