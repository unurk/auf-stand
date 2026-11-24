"""Ist die Live-Seite aktuell? — Entscheidung für (Nach-)Deploys auf GitHub Pages.

Vorfall 24.11.2026 (Lauf 45330313914): upload-pages-artifact meldete das
Artifact um 05:01:55.329 als hochgeladen, deploy-pages fragte 370 ms später
die Artifact-Liste ab und bekam „Found 0 artifact(s)" — die Liste war noch
nicht nachgezogen (das Artifact ist dort heute gelistet). Wegen
continue-on-error blieb der Lauf grün, und weil sich site/ danach nicht mehr
änderte, deployte auch kein Wiederhol-Cron nach: Die Seite stand bis zur
nächsten Ausgabe auf dem Vortag.

Die GitHub-Deployments (Environment „github-pages") taugen nicht als Beleg,
was live ist: Sie stehen auf „success", sobald der JOB grün ist — auch wenn
der Deploy-Schritt gescheitert ist. Darum ist die Live-Seite selbst die
Quelle: Jeder Deploy legt ``deploy.json`` mit dem Git-Tree-Hash von site/
bei. Ein späterer Lauf vergleicht ihn mit HEAD und deployt nur, wenn die
Live-Seite hinterherhinkt — bei aktuellem Stand gibt es keinen Deploy.
"""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone

MARKER = "deploy.json"


def site_tree(pfad: str = "site") -> str:
    """Git-Tree-Hash des Verzeichnisses in HEAD — ändert sich genau mit dem Inhalt."""
    return subprocess.run(
        ["git", "rev-parse", f"HEAD:{pfad}"], check=True, capture_output=True, text=True,
    ).stdout.strip()


def schreibe_marker(ziel: str = "site", tree: str | None = None) -> dict:
    """deploy.json ins Artifact legen (nicht committet, siehe .gitignore)."""
    daten = {
        "site_tree": tree or site_tree(ziel),
        "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                 text=True).stdout.strip(),
        "erstellt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with open(f"{ziel}/{MARKER}", "w", encoding="utf-8") as fh:
        json.dump(daten, fh)
    return daten


def live_tree(site_url: str, http_get=None) -> str | None:
    """site_tree der Live-Seite — None, wenn nicht lesbar (Netz, 404, kein Marker)."""
    if http_get is None:
        import httpx
        http_get = httpx.get
    url = site_url.rstrip("/") + f"/{MARKER}?t={int(time.time())}"  # am CDN-Cache vorbei
    try:
        r = http_get(url, timeout=15, follow_redirects=True)
        if r.status_code != 200:
            return None
        return str(r.json().get("site_tree") or "") or None
    except Exception:
        return None


def muss_deployen(site_geaendert: bool, live: str | None, head: str) -> tuple[bool, str]:
    """(deployen?, Begründung) — die Nachdeploy-Entscheidung."""
    if site_geaendert:
        return True, "site/ in diesem Lauf geändert."
    if live is None:
        return True, "Live-Stand nicht lesbar (kein deploy.json) — Deploy zur Sicherheit."
    if live != head:
        return True, (f"Live-Seite hinkt hinterher (live {live[:7]}, HEAD {head[:7]}) — "
                      "ein früherer Deploy ist gescheitert, Nachdeploy.")
    return False, "Live-Seite ist aktuell — kein Deploy."


def cmd_pages_check(config: dict, site_geaendert: bool, ausgabe=None, http_get=None) -> int:
    """Schreibt deploy=true|false nach $GITHUB_OUTPUT (bzw. stdout) und den Marker."""
    import os

    head = site_tree()
    live = None if site_geaendert else live_tree(
        config.get("site_url", "https://unurk.github.io/auf-stand/"), http_get)
    deploy, grund = muss_deployen(site_geaendert, live, head)
    print(f"Pages-Check: {grund}")
    if deploy:
        schreibe_marker(tree=head)
    ziel = ausgabe or os.environ.get("GITHUB_OUTPUT")
    zeile = f"deploy={'true' if deploy else 'false'}\n"
    if ziel:
        with open(ziel, "a", encoding="utf-8") as fh:
            fh.write(zeile)
    else:
        print(zeile, end="")
    return 0
