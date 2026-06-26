"""Formatiert WHOOP-Daten in Prompt-Blöcke und ruft Claude auf."""
from __future__ import annotations

import os
from pathlib import Path

from .client import DayData

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"


def _fmt(days: list[DayData]) -> str:
    lines: list[str] = []
    for d in days:
        parts = [f"## {d.date}"]

        if d.recovery_score is not None:
            zone = (
                "Grün (bereit)"
                if d.recovery_score >= 67
                else "Gelb (moderat)"
                if d.recovery_score >= 34
                else "Rot (erholen)"
            )
            rec_parts = [f"Recovery {d.recovery_score}% [{zone}]"]
            if d.hrv_ms is not None:
                rec_parts.append(f"HRV {d.hrv_ms:.1f} ms")
            if d.rhr is not None:
                rec_parts.append(f"RHR {d.rhr} bpm")
            if d.spo2 is not None:
                rec_parts.append(f"SpO₂ {d.spo2:.1f}%")
            if d.skin_temp is not None:
                rec_parts.append(f"Hauttemp. {d.skin_temp:.1f}°C")
            parts.append("Recovery: " + " · ".join(rec_parts))
        else:
            parts.append("Recovery: keine Daten")

        if d.sleep_hours is not None:
            sl = [f"{d.sleep_hours:.1f}h Schlaf"]
            if d.sleep_needed_hours:
                sl.append(f"(Bedarf {d.sleep_needed_hours:.1f}h)")
            if d.sleep_performance is not None:
                sl.append(f"Performance {d.sleep_performance}%")
            if d.sleep_efficiency is not None:
                sl.append(f"Effizienz {d.sleep_efficiency}%")
            if d.deep_sleep_hours is not None:
                sl.append(f"Tiefschlaf {d.deep_sleep_hours:.1f}h")
            if d.rem_hours is not None:
                sl.append(f"REM {d.rem_hours:.1f}h")
            if d.sleep_disturbances is not None:
                sl.append(f"{d.sleep_disturbances} Unterbrechungen")
            if d.sleep_cycles is not None:
                sl.append(f"{d.sleep_cycles} Schlafzyklen")
            if d.respiratory_rate is not None:
                sl.append(f"Atemfrequenz {d.respiratory_rate:.1f}/min")
            parts.append("Schlaf: " + " · ".join(sl))
        else:
            parts.append("Schlaf: keine Daten")

        if d.workouts:
            for w in d.workouts:
                wo = [w.sport]
                if w.strain is not None:
                    wo.append(f"Strain {w.strain:.1f}")
                if w.avg_hr:
                    wo.append(f"øHR {w.avg_hr}")
                if w.max_hr:
                    wo.append(f"MaxHR {w.max_hr}")
                if w.kcal:
                    wo.append(f"{w.kcal:.0f} kcal")
                parts.append("Training: " + " · ".join(wo))
        else:
            parts.append("Training: kein Workout aufgezeichnet")

        if d.day_strain is not None:
            strain_label = (
                "sehr hoch" if d.day_strain >= 18
                else "hoch" if d.day_strain >= 14
                else "moderat" if d.day_strain >= 7
                else "leicht/Erholung"
            )
            strain_line = f"Tages-Strain: {d.day_strain:.1f} [{strain_label}]"
            if d.day_kcal:
                strain_line += f" · {d.day_kcal:.0f} kcal gesamt"
            parts.append(strain_line)

        lines.append("\n".join(parts))

    return "\n\n".join(lines)


def build_prompt(days: list[DayData], mode: str) -> str:
    template = (PROMPTS_DIR / f"{mode}.md").read_text(encoding="utf-8")
    return template + "\n\n" + _fmt(days)


def call_claude(prompt: str, model: str = "claude-haiku-4-5-20251001", max_tokens: int = 1200) -> str:
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY fehlt — in .env eintragen.")
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()
