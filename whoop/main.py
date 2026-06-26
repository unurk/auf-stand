"""CLI: python -m whoop.main auth|heute|woche [--dry-run]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent


def main() -> int:
    load_dotenv(BASE_DIR / ".env")

    parser = argparse.ArgumentParser(description="WHOOP × Claude — Gesundheitsanalyse")
    parser.add_argument("command", choices=["auth", "heute", "woche"])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prompt bauen und speichern, kein Claude-API-Call",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Anzahl Tage Verlauf (Standard: 7)",
    )
    args = parser.parse_args()

    if args.command == "auth":
        from .auth import run_auth_flow
        run_auth_flow()
        return 0

    from . import analyse, render
    from .client import fetch_days

    print(f"Lade WHOOP-Daten der letzten {args.days} Tage …")
    days = fetch_days(days=args.days)

    if not days:
        print("Keine WHOOP-Daten gefunden.")
        return 1

    print(f"{len(days)} Tage geladen.")

    mode = args.command
    prompt = analyse.build_prompt(days, mode)

    if args.dry_run:
        out = render.OUT_DIR
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{mode}-prompt.txt"
        path.write_text(prompt, encoding="utf-8")
        print(f"Dry-Run: Prompt gespeichert → {path}")
        return 0

    print("Claude analysiert …")
    result = analyse.call_claude(prompt, max_tokens=1500 if mode == "woche" else 1000)
    path = render.write(result, mode)
    print("\n" + result + f"\n\n→ Gespeichert: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
