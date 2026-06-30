"""Schreibt das Lagebild als Markdown und schlicht gestaltetes HTML nach out/."""
from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path

from . import i18n

OUT_DIR = Path(__file__).resolve().parent.parent / "out"
_BASE_DIR = Path(__file__).resolve().parent.parent


def set_out_dir(path: str | None) -> None:
    """Setzt das Ausgabeverzeichnis (z. B. 'out/nyt' für die NYT-Edition)."""
    global OUT_DIR
    if not path:
        return
    p = Path(path)
    OUT_DIR = p if p.is_absolute() else _BASE_DIR / p

HTML_TEMPLATE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ margin: 0; background: #ffffff; font-family: Georgia, 'Times New Roman', serif;
         color: #121212; line-height: 1.6; }}
  .wrap {{ max-width: 620px; margin: 0 auto; padding: 32px 20px 48px; }}
  .brand {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
            font-size: 13px; letter-spacing: 0.14em; text-transform: uppercase;
            color: #8a8378; margin-bottom: 28px; }}
  h1 {{ font-size: 28px; line-height: 1.2; margin: 0 0 12px; }}
  .byline {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
            font-size: 13px; color: #6b6b6b; margin: 0 0 24px; padding-bottom: 16px;
            border-bottom: 1px solid #e3e1dc; }}
  h2 {{ font-size: 19px; margin: 28px 0 8px; }}
  p {{ margin: 0 0 12px; font-size: 17px; }}
  strong {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
            font-size: 13px; letter-spacing: 0.04em; text-transform: uppercase;
            color: #6b6458; }}
  .done {{ margin-top: 36px; padding: 14px 18px; background: #ffffff;
           border: 1px solid #e2ddd4; border-radius: 10px;
           font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
           font-size: 15px; color: #2e6b3f; }}
  hr {{ border: none; border-top: 1px solid #e2ddd4; margin: 28px 0; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="brand">{brand}</div>
  {body}
</div>
</body>
</html>
"""


def _markdown_to_html(markdown: str, lang: str = "de") -> str:
    """Bewusst minimaler Konverter fuer das bekannte Lagebild-Format."""
    informed = i18n.t(lang, "informed_marker")
    out: list[str] = []
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("---"):
            out.append("<hr>")
            continue
        escaped = html.escape(line)
        escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
        if line.startswith("# "):
            out.append(f"<h1>{escaped[2:]}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{escaped[3:]}</h2>")
        elif informed in line:
            plain = re.sub(r"</?em>", "", escaped).strip()
            out.append(f'<div class="done">{plain}</div>')
        else:
            out.append(f"<p>{escaped}</p>")
    return "\n  ".join(out)


def insert_reporters_footer(markdown: str, lang: str = "de") -> str:
    """Sammelt die je Punkt genannten Reporter-Namen zu einer Fußzeile.

    Zählt nur, was tatsächlich im Text steht (keine erfundenen Namen). Setzt die Zeile
    direkt vor die „informiert"-Abschlusszeile, sonst ans Ende.
    """
    join_word = i18n.t(lang, "reporters_join")
    informed = i18n.t(lang, "informed_marker")
    names: list[str] = []
    for m in re.finditer(i18n.t(lang, "reporters_marker"), markdown):
        name = m.group(1).strip()
        if name and name not in names:
            names.append(name)
    if not names:
        return markdown
    if len(names) == 1:
        joined = names[0]
    elif len(names) == 2:
        joined = f"{names[0]} {join_word} {names[1]}"
    else:
        joined = ", ".join(names[:-1]) + f" {join_word} {names[-1]}"
    footer = i18n.t(lang, "reporters_footer_fmt").format(names=joined)
    lines = markdown.splitlines()
    for i, line in enumerate(lines):
        if informed in line:
            lines.insert(i, footer)
            lines.insert(i + 1, "")
            return "\n".join(lines)
    return markdown.rstrip() + "\n\n" + footer


def write_output(markdown: str, edition: str, lang: str = "de") -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    md_path = OUT_DIR / f"{stamp}-{edition}.md"
    html_path = OUT_DIR / f"{stamp}-{edition}.html"
    md_path.write_text(markdown + "\n", encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    title = title_match.group(1) if title_match else i18n.t(lang, "default_title")
    body = _markdown_to_html(markdown, lang)
    body = body.replace(
        "</h1>", f'</h1>\n  <p class="byline">{i18n.t(lang, "byline")}</p>', 1
    )
    html_path.write_text(
        HTML_TEMPLATE.format(
            title=html.escape(title),
            body=body,
            lang=i18n.t(lang, "html_lang"),
            brand=i18n.t(lang, "brand"),
        ),
        encoding="utf-8",
    )
    return md_path, html_path
