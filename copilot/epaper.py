"""Stellt den Link zur E-Paper-Ausgabe bereit.

Die direkte Ausgaben-URL (mit Issue-ID) ist auth-gated und ohne Login nicht
zuverlässig zu ermitteln. Wir verlinken daher die offizielle E-Paper-Seite —
Die Presse leitet eingeloggte Abonnent:innen selbst zur aktuellen Ausgabe.
Über config.yaml (`epaper_url`) überschreibbar.
"""
from __future__ import annotations

from . import i18n

_DEFAULT_URL = "https://www.diepresse.com/epaper"


def get_epaper_url(config: dict | None = None) -> str:
    if config and config.get("epaper_url"):
        return str(config["epaper_url"])
    return _DEFAULT_URL


def epaper_section(url: str, lang: str = "de") -> str:
    """Gibt den Markdown-Block für den E-Paper-Link zurück."""
    label = i18n.t(lang, "epaper_label")
    link_text = i18n.t(lang, "epaper_link_text")
    return f"\n---\n\n📰 **{label}** · [{link_text}]({url})"
