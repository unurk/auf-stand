"""Pages-Deploy heilt sich selbst (Vorfall 24.11.: Deploy gescheitert, Seite blieb alt)."""
import json
import subprocess
from pathlib import Path

import yaml

from copilot import pages

ROOT = Path(__file__).resolve().parent.parent


class _Antwort:
    def __init__(self, status, daten=None):
        self.status_code = status
        self._daten = daten

    def json(self):
        if self._daten is None:
            raise ValueError("kein JSON")
        return self._daten


# ── Die Entscheidung ─────────────────────────────────────────────────────────

def test_geaenderte_site_wird_deployt():
    assert pages.muss_deployen(True, "abc", "abc")[0] is True


def test_gescheiterter_deploy_wird_nachgeholt():
    # 24.11.: site/ in HEAD neu, live noch der Vortag — Wiederhol-Cron ohne Änderung
    deploy, grund = pages.muss_deployen(False, "alt1234", "neu5678")
    assert deploy and "hinkt hinterher" in grund


def test_aktuelle_seite_kein_leerer_deploy():
    deploy, grund = pages.muss_deployen(False, "neu5678", "neu5678")
    assert deploy is False and "aktuell" in grund


def test_unlesbarer_live_stand_deployt_zur_sicherheit():
    assert pages.muss_deployen(False, None, "neu5678")[0] is True


# ── Live-Stand lesen ─────────────────────────────────────────────────────────

def test_live_tree_liest_marker_am_cache_vorbei():
    urls = []

    def get(url, timeout=15, follow_redirects=True):
        urls.append(url)
        return _Antwort(200, {"site_tree": "abc123"})
    assert pages.live_tree("https://x.example/auf-stand/", get) == "abc123"
    assert urls[0].startswith("https://x.example/auf-stand/deploy.json?t=")


def test_live_tree_fehlerfaelle_sind_none():
    assert pages.live_tree("https://x", lambda u, **k: _Antwort(404)) is None
    assert pages.live_tree("https://x", lambda u, **k: _Antwort(200)) is None  # kein JSON

    def offline(url, **k):
        raise OSError("offline")
    assert pages.live_tree("https://x", offline) is None


# ── Ende zu Ende in einem Wegwerf-Repo ───────────────────────────────────────

def _repo(tmp_path):
    def git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.email", "t@example.invalid")
    git("config", "user.name", "Test")
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "index.html").write_text("Abend 23.11.")
    git("add", ".")
    git("commit", "-qm", "alt")
    alt = subprocess.run(["git", "rev-parse", "HEAD:site"], cwd=tmp_path,
                         capture_output=True, text=True).stdout.strip()
    (tmp_path / "site" / "index.html").write_text("Morgen 24.11.")
    git("commit", "-qam", "neu")
    return alt


def _check(tmp_path, monkeypatch, live, geaendert=False):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "gh_output"
    get = lambda url, **k: _Antwort(200, {"site_tree": live})  # noqa: E731
    pages.cmd_pages_check({"site_url": "https://x.example/"}, geaendert, str(out), get)
    return out.read_text()


def test_wiederhol_cron_deployt_nach_und_schreibt_marker(tmp_path, monkeypatch):
    alt = _repo(tmp_path)
    assert _check(tmp_path, monkeypatch, live=alt) == "deploy=true\n"
    marker = json.loads((tmp_path / "site" / "deploy.json").read_text())
    assert marker["site_tree"] == pages.site_tree() != alt


def test_wiederhol_cron_bei_aktuellem_stand_ohne_deploy(tmp_path, monkeypatch):
    _repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    aktuell = pages.site_tree()
    assert _check(tmp_path, monkeypatch, live=aktuell) == "deploy=false\n"
    assert not (tmp_path / "site" / "deploy.json").exists()


# ── Workflows ────────────────────────────────────────────────────────────────

def _steps(datei):
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / datei).read_text(encoding="utf-8"))
    job = next(iter(wf["jobs"].values()))
    return {s.get("name"): s for s in job["steps"]}


def test_workflows_pruefen_wiederholen_und_melden():
    for datei in ("lagebild.yml", "nyt.yml"):
        steps = _steps(datei)
        check = steps["Pages-Stand prüfen"]
        assert "pages-check" in check["run"] and "--ff-only" in check["run"]
        for name in ("GitHub Pages hochladen", "GitHub Pages deployen"):
            assert "steps.pages.outputs.deploy == 'true'" in steps[name]["if"]
            assert "changed" not in steps[name]["if"]
        zweiter = steps["GitHub Pages deployen (2. Versuch)"]
        assert zweiter["uses"].startswith("actions/deploy-pages@")
        assert "steps.pages-deployment.outcome == 'failure'" in zweiter["if"]
        alarm = steps["Pages-Deploy-Fehler melden"]
        assert "steps.pages-deployment-2.outcome != 'success'" in alarm["if"]
        assert "TELEGRAM_BOT_TOKEN" in alarm["env"] and "sendMessage" in alarm["run"]


def test_marker_ist_nicht_im_repo():
    assert "site/deploy.json" in (ROOT / ".gitignore").read_text()
