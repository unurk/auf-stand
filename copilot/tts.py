"""Audio-Ausgabe: liest das Lagebild via OpenAI TTS vor (mp3 nach out/).

Best-effort: Schlägt der TTS-Call fehl, bleibt der bereits zugestellte
Text-Versand unberührt. Nutzt das vorhandene httpx statt eines eigenen SDK,
um die Abhängigkeiten minimal zu halten (CLAUDE.md-Konvention).
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

import httpx

from .render import OUT_DIR

_API_URL = "https://api.openai.com/v1/audio/speech"
_DEFAULT_MODEL = "gpt-4o-mini-tts"
_DEFAULT_VOICE = "alloy"
_DEFAULT_INSTRUCTIONS = (
    "Sprich ruhig und sachlich, im Tempo einer seriösen Nachrichtensprecherin."
)
# OpenAI-Limit liegt bei 4096 Zeichen je Anfrage — etwas Puffer lassen.
_CHUNK_LIMIT = 3800

# Emoji + Variation-Selektoren + Keycap-Kombis (1️⃣) abdecken.
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF\U00002B00-\U00002BFF\U0000FE00-\U0000FE0F"
    "\U000020E0-\U000020FF\U00002300-\U000023FF]+",
    flags=re.UNICODE,
)


def tts_configured(config: dict | None = None) -> bool:
    """True, wenn ein OpenAI-Key vorhanden und TTS nicht hart abgeschaltet ist."""
    if config is not None and not config.get("tts", {}).get("enabled", True):
        return False
    return bool(os.environ.get("OPENAI_API_KEY"))


def _to_speech_text(markdown: str) -> str:
    """Macht aus dem Lagebild-Markdown saubere, vorlesbare Prosa.

    Entfernt Markup, Emoji, Links/URLs, den E-Paper-Footer, die „Heute wichtig"-
    Übersicht (würde die Schlagzeilen doppelt vorlesen) und die Lesezeit-Zeile.
    """
    lines: list[str] = []
    in_summary = False
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        # „Heute wichtig:"-Übersichtsblock überspringen (Schlagzeilen kommen unten voll).
        if line.startswith("**Heute wichtig"):
            in_summary = True
            continue
        if in_summary:
            if line.startswith("---") or line.startswith("#"):
                in_summary = False
            else:
                continue  # die 1️⃣/2️⃣-Übersichtszeilen
        # Trennlinien → Absatz/Pause.
        if line.startswith("---"):
            lines.append("")
            continue
        # E-Paper-Footer komplett weglassen.
        if "E-Paper" in line:
            continue
        # Abschluss-Zeile: nur „Du bist informiert." behalten, Lesezeit/Verweis weg.
        if "informiert" in line and "Lesezeit" in line:
            lines.append("Du bist informiert.")
            continue
        # Links: nur den sichtbaren Text behalten, URL verwerfen.
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        # „→ Artikel"-Reste und nackte URLs entfernen.
        line = re.sub(r"→\s*Artikel", "", line)
        line = re.sub(r"https?://\S+", "", line)
        # Bold/Italic-Marker entfernen (Label-Text wie „Was ist neu:" bleibt).
        line = line.replace("**", "").replace("__", "")
        line = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", line)
        # Überschriften: Markdown-Präfix weg; Titel als eigener Satz.
        heading = bool(re.match(r"#{1,6}\s", line))
        line = re.sub(r"^#{1,6}\s*", "", line)
        # Listen-Bullets entfernen.
        line = re.sub(r"^[-*]\s+", "", line)
        # Emoji raus, dann Mehrfach-Leerzeichen normalisieren.
        line = _EMOJI_RE.sub("", line)
        line = re.sub(r"\s{2,}", " ", line).strip(" ·-—")
        # Übrig gebliebene Punkt-Nummer (aus „## 1️⃣ …") am Zeilenanfang entfernen.
        if heading:
            line = re.sub(r"^\d{1,2}[.):]?\s+", "", line).strip()
        if not line:
            continue
        # Überschriften ohne Satzzeichen abschließen → klare Sprechpause.
        if heading and not line.endswith((".", "!", "?", ":")):
            line += "."
        lines.append(line)

    # Mehrfache Leerzeilen zu einzelnen Absatztrennern verdichten.
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _chunks(text: str, limit: int = _CHUNK_LIMIT) -> list[str]:
    """Teilt langen Text an Absatz-, notfalls Satzgrenzen (max. `limit` Zeichen)."""
    if len(text) <= limit:
        return [text]
    # Absätze; überlange Einzelabsätze zusätzlich satzweise zerlegen.
    units: list[str] = []
    for para in text.split("\n\n"):
        if len(para) <= limit:
            units.append(para)
            continue
        buf = ""
        for sentence in re.split(r"(?<=[.!?])\s+", para):
            if buf and len(buf) + len(sentence) + 1 > limit:
                units.append(buf)
                buf = ""
            buf = f"{buf} {sentence}" if buf else sentence
        if buf:
            units.append(buf)
    out: list[str] = []
    current = ""
    for unit in units:
        if current and len(current) + len(unit) + 2 > limit:
            out.append(current)
            current = ""
        current = f"{current}\n\n{unit}" if current else unit
    if current:
        out.append(current)
    return out


def synthesize_audio(text: str, out_path: Path, config: dict | None = None) -> Path | None:
    """Ruft OpenAI TTS auf und schreibt die mp3. Gibt den Pfad oder None zurück."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or not text.strip():
        return None
    tts_cfg = (config or {}).get("tts", {})
    model = tts_cfg.get("model", _DEFAULT_MODEL)
    voice = tts_cfg.get("voice", _DEFAULT_VOICE)
    instructions = tts_cfg.get("instructions", _DEFAULT_INSTRUCTIONS)
    headers = {"Authorization": f"Bearer {api_key}"}

    audio = bytearray()
    for chunk in _chunks(text):
        payload = {
            "model": model,
            "voice": voice,
            "input": chunk,
            "response_format": "mp3",
        }
        if instructions:
            payload["instructions"] = instructions
        try:
            resp = httpx.post(_API_URL, headers=headers, json=payload, timeout=120)
        except Exception as exc:
            print(f"TTS-Fehler (Netzwerk): {exc}")
            return None
        if resp.status_code != 200:
            detail = resp.text[:200]
            print(f"TTS-Fehler ({resp.status_code}): {detail}")
            return None
        audio.extend(resp.content)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(bytes(audio))
    print(f"Audio erzeugt: {out_path} ({len(audio) // 1024} KB)")
    return out_path


def generate_lagebild_audio(
    lagebild: str, edition: str, config: dict | None = None
) -> Path | None:
    """Erzeugt aus dem fertigen Lagebild die mp3 unter out/<datum>-<edition>.mp3."""
    text = _to_speech_text(lagebild)
    out_path = OUT_DIR / f"{datetime.now():%Y-%m-%d}-{edition}.mp3"
    return synthesize_audio(text, out_path, config)
