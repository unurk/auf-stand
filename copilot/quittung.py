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

    # Lese-Tage schlagen Zustell-Tage: Ein Streak, den unser Cron erzeugt, misst
    # uns. Solange es keine Lese-Signale gibt, bleibt es beim Zustell-Bild.
    read_dates = {
        e["date"] for e in state.get("read_events", []) if e.get("date", "") >= cutoff
    }
    active_dates = read_dates or {s["date"] for s in week}
    days = [
        (WEEKDAY_LABELS[d.weekday()], d.isoformat() in active_dates)
        for d in window
    ]
    words = sum(s["words"] for s in week)
    # Time-to-Informed: die tatsächlich gemessene Lesezeit der Ausgaben. Für
    # Altbestände ohne `secs` fällt es auf die Wortzahl zurück.
    sekunden = sum(s.get("secs") or 0 for s in week)
    if not sekunden:
        sekunden = round(words / LESETEMPO_WOERTER_PRO_MINUTE * 60)
    geprueft = sum(s.get("geprueft") or s.get("new_articles", 0) for s in week)
    return {
        "articles": sum(s["new_articles"] for s in week),
        "geprueft": geprueft,
        "points": sum(s["points"] for s in week),
        "editions": len(week),
        "minutes": max(1, round(words / LESETEMPO_WOERTER_PRO_MINUTE)),
        "sekunden": sekunden,
        "zeit_label": _zeit_label(sekunden),
        "days": days,
        "days_on_stand": len(active_dates),
        "misst_lesen": bool(read_dates),
        "range_label": _range_label(window[0], today),
        "feedback": state_module.feedback_summary(state, cutoff),
    }


def _zeit_label(sekunden: int) -> str:
    """„6 Min 40" — die Kennzahl, um die es geht: Time-to-Informed."""
    minuten, rest = divmod(max(0, int(sekunden)), 60)
    if minuten == 0:
        return f"{rest} Sek"
    return f"{minuten}:{rest:02d} Min"


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
    fig.text(0.5, 0.93, "DIE PRESSE · COPILOT", ha="center",
             fontsize=15, color=MUTED, family="sans-serif")
    fig.text(0.5, 0.855, "Deine Wochen-Quittung", ha="center",
             fontsize=44, color=INK, family="serif", weight="bold")
    fig.text(0.5, 0.81, stats["range_label"], ha="center",
             fontsize=17, color=MUTED, family="sans-serif")

    # Drei grosse Kennzahlen — die mittlere ist die eigentliche Produktkennzahl
    # (Time-to-Informed), nicht unsere Produktionsleistung.
    cols = [
        (0.21, f"{stats['geprueft']}", "Meldungen\ngeprüft", MUTED),
        (0.50, stats["zeit_label"], "warst du\nauf Stand", ACCENT),
        (0.79, f"{stats['points']}", "Entwicklungen\ndie zählten", MUTED),
    ]
    for x, number, label, color in cols:
        fig.text(x, 0.63, number, ha="center",
                 fontsize=78 if len(str(number)) <= 4 else 60,
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
             f"Du warst {stats['days_on_stand']} von 7 Tagen informiert"
             + ("" if stats.get("misst_lesen") else " (zugestellt)"),
             ha="center", fontsize=24, color=GREEN, family="serif", weight="bold")
    fig.text(0.5, 0.115,
             f"{stats['geprueft']} Meldungen gelesen, {stats['points']} für dich behalten — "
             f"in {stats['zeit_label']} statt stundenlangem Scrollen.",
             ha="center", fontsize=15, color=MUTED, family="sans-serif")

    fb = stats.get("feedback", {})
    if fb.get("total"):
        fig.text(0.5, 0.065,
                 f"Du fandest {fb['up']} von {fb['total']} bewerteten Ausgaben relevant.",
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
        f"📬 Deine Wochen-Quittung: {stats['geprueft']} Meldungen geprüft, "
        f"{stats['points']} Entwicklungen behalten — du warst in {stats['zeit_label']} "
        f"auf Stand. {stats['days_on_stand']}/7 Tage informiert ✓"
    )
    telegram.send_photo(image, caption, config.get("telegram_chat_ids", []))
    print(f"Quittung erzeugt: {image}")

    if config.get("quiz_enabled", True):
        _wochen_quiz(current_state, config)
    return 0


def _wochen_quiz(state: dict, config: dict) -> None:
    """Drei Fragen zur Woche — misst Informiertheit statt Zustellung (best-effort)."""
    from . import synthesize

    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat()
    material: list[str] = []
    for key, headings in state.get("edition_points", {}).items():
        if key.split("|")[0] >= cutoff:
            material.extend(headings)
    for eintraege in state.get("dossier", {}).values():
        material.extend(e["summary"] for e in eintraege if e.get("date", "") >= cutoff)
    if len(material) < 3:
        print("Zu wenig Stoff für ein Wochen-Quiz — übersprungen.")
        return
    lang = config.get("language", "de")
    try:
        fragen = synthesize.generate_quiz(material, config, lang)
    except Exception as exc:
        print(f"Wochen-Quiz übersprungen: {exc}")
        return
    if not fragen:
        print("Kein Quiz erzeugt — übersprungen.")
        return
    chat_ids = config.get("telegram_chat_ids", [])
    gesendet = 0
    for f in fragen:
        if telegram.send_quiz(
            f["frage"], f["optionen"], f["richtig"], chat_ids, f.get("erklaerung", "")
        ):
            gesendet += 1
    print(f"Wochen-Quiz: {gesendet} Frage(n) gesendet.")
