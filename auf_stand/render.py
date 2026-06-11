"""Schreibt das Lagebild als Markdown und schlicht gestaltetes HTML nach out/."""
from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "out"

HTML_TEMPLATE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ margin: 0; background: #f5f3ef; font-family: Georgia, 'Times New Roman', serif;
         color: #1a1a1a; line-height: 1.55; }}
  .wrap {{ max-width: 620px; margin: 0 auto; padding: 32px 20px 48px; }}
  .brand {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
            font-size: 13px; letter-spacing: 0.14em; text-transform: uppercase;
            color: #8a8378; margin-bottom: 28px; }}
  h1 {{ font-size: 26px; line-height: 1.25; margin: 0 0 24px; }}
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
  <div class="brand">Die Presse · Auf Stand</div>
  {body}
</div>
</body>
</html>
"""


def _markdown_to_html(markdown: str) -> str:
    """Bewusst minimaler Konverter fuer das bekannte Lagebild-Format."""
    out: list[str] = []
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("---"):
            out.append("<hr>")
            continue
        escaped = html.escape(line)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
        if line.startswith("# "):
            out.append(f"<h1>{escaped[2:]}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{escaped[3:]}</h2>")
        elif "auf Stand ✓" in line:
            out.append(f'<div class="done">{escaped.strip("<em></em>")}</div>')
        else:
            out.append(f"<p>{escaped}</p>")
    return "\n  ".join(out)


def write_output(markdown: str, edition: str) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    md_path = OUT_DIR / f"{stamp}-{edition}.md"
    html_path = OUT_DIR / f"{stamp}-{edition}.html"
    md_path.write_text(markdown + "\n", encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    title = title_match.group(1) if title_match else "Dein Lagebild"
    html_path.write_text(
        HTML_TEMPLATE.format(title=html.escape(title), body=_markdown_to_html(markdown)),
        encoding="utf-8",
    )
    return md_path, html_path
