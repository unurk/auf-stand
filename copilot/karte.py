"""Teilbare Punkt-Karte: der wichtigste Punkt einer Ausgabe als Bild.

Weiterleiten ist heute Copy-Paste. Eine Bild-Karte macht daraus etwas, das in
einen Familien- oder Team-Chat wandert — und sie verlängert keine Session,
sondern exportiert sie. Für die „Presse" ist das der einzige organische
Verbreitungsweg, den ein Hintergrund-Dienst überhaupt haben kann.

Rendert bewusst mit demselben matplotlib-Ansatz wie die Wochen-Quittung
(keine neue Abhängigkeit) und in derselben Presse-Optik.
"""
from __future__ import annotations

import re
import textwrap
from datetime import date
from pathlib import Path

from . import i18n

OUT_DIR = Path(__file__).resolve().parent.parent / "out"

BG = "#f5f3ef"
INK = "#1a1a1a"
MUTED = "#8a8378"
ACCENT = "#b5543b"

# Emoji rendern in matplotlib nicht zuverlässig — vor dem Zeichnen entfernen.
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002190-\U000021FF\U00002300-\U000027BF️⃣]+"
)


def _clean(text: str) -> str:
    text = _EMOJI_RE.sub("", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # Markdown-Links
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def top_punkt(markdown: str) -> dict | None:
    """Zieht Titel, Kern und Reifegrad des ersten Punktes aus dem Lagebild."""
    lines = markdown.splitlines()
    start = next(
        (i for i, l in enumerate(lines) if l.startswith("## ") and re.match(r"## [1１1️⃣]", l)),
        None,
    )
    if start is None:
        return None
    titel = _clean(re.sub(r"^##\s*\S*\s*", "", lines[start]))
    body: list[str] = []
    reifegrad = ""
    for line in lines[start + 1 :]:
        if line.startswith("## ") or line.startswith("---"):
            break
        m = re.match(r"\*\*(Reifegrad|Status):\*\*\s*(.+)", line.strip())
        if m:
            reifegrad = _clean(m.group(2))
            continue
        if line.strip().startswith("**Was ist neu:**") or line.strip().startswith("**What's new:**"):
            body.append(_clean(re.sub(r"\*\*[^*]+:\*\*", "", line)))
    if not titel:
        return None
    kern = body[0] if body else ""
    # Auf die ersten beiden Sätze kürzen — eine Karte ist kein Artikel.
    saetze = re.split(r"(?<=[.!?])\s+", kern)
    kern = " ".join(saetze[:2])
    return {"titel": titel, "kern": kern, "reifegrad": reifegrad}


def build_karte(
    punkt: dict, datum: date, edition_label: str, path: Path, lang: str = "de"
) -> Path:
    """Zeichnet die Karte (1080×1080) und legt sie unter `path` ab."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    weekdays = i18n.t(lang, "weekdays")
    months = i18n.t(lang, "months")
    if lang == "en":
        datum_label = f"{weekdays[datum.weekday()]}, {months[datum.month - 1]} {datum.day}"
    else:
        datum_label = f"{weekdays[datum.weekday()]}, {datum.day}. {months[datum.month - 1]}"

    fig = plt.figure(figsize=(10.8, 10.8), dpi=100)
    fig.patch.set_facecolor(BG)

    fig.text(0.08, 0.93, i18n.t(lang, "brand").upper(), fontsize=15, color=MUTED,
             family="sans-serif", va="top")
    fig.text(0.08, 0.885, f"{datum_label} · {edition_label}", fontsize=16, color=MUTED,
             family="sans-serif", va="top")

    zeilen = textwrap.wrap(punkt["titel"], width=26)[:4]
    fig.text(0.08, 0.79, "\n".join(zeilen), fontsize=46, color=INK, family="serif",
             weight="bold", va="top", linespacing=1.25)

    if punkt.get("kern"):
        # Fließtext an der tatsächlichen Titelhöhe ausrichten, sonst klafft bei
        # kurzen Schlagzeilen ein Loch in der Karte.
        y = 0.79 - 0.075 * len(zeilen) - 0.07
        kern = "\n".join(textwrap.wrap(punkt["kern"], width=44)[:7])
        fig.text(0.08, y, kern, fontsize=22, color=INK, family="sans-serif",
                 va="top", linespacing=1.6)

    if punkt.get("reifegrad"):
        fig.text(0.08, 0.155, punkt["reifegrad"].upper(), fontsize=15, color=ACCENT,
                 family="sans-serif", weight="bold", va="top")

    fig.text(0.08, 0.09, i18n.t(lang, "karte_footer"), fontsize=16, color=MUTED,
             family="sans-serif", va="top")
    # Akzentlinie unten links als ruhiger Marken-Anker
    fig.add_artist(plt.Line2D([0.08, 0.22], [0.115, 0.115], color=ACCENT, linewidth=3))

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=BG, bbox_inches="tight", pad_inches=0.35)
    plt.close(fig)
    return path


def karte_fuer_ausgabe(
    markdown: str,
    edition: str,
    edition_label: str,
    datum: date | None = None,
    out_dir: Path | None = None,
    lang: str = "de",
) -> Path | None:
    """Erzeugt die Karte zum wichtigsten Punkt — None, wenn es keinen gibt."""
    punkt = top_punkt(markdown)
    if not punkt:
        return None
    d = datum or date.today()
    ziel = (out_dir or OUT_DIR) / f"{d.isoformat()}-{edition}-karte.png"
    try:
        return build_karte(punkt, d, edition_label, ziel, lang)
    except Exception as exc:  # Bildbau darf den Versand nie blockieren
        print(f"Karte übersprungen: {exc}")
        return None
