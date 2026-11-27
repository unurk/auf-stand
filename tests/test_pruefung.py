"""Täglicher Qualitätscheck (Übergabe ohne Bot ab 1.12.2026)."""
import shutil
from datetime import date, datetime
from pathlib import Path

import yaml

from copilot import pruefung, slot

ROOT = Path(__file__).resolve().parent.parent
CONFIG = {"editions": {"morgen": {"time": "06:00"}}, "lesezeit_budget_sekunden": 90}


def _um(datum: date, h: int, m: int):
    return lambda pfad: datetime(datum.year, datum.month, datum.day, h, m, tzinfo=slot.WIEN)


def _seite(punkte, h1="Gericht kippt Mietpreisdeckel", heute=None, lesezeit=90):
    heute = heute if heute is not None else [t for t, _, _ in punkte]
    hl = "".join(f"<p>{t}</p>" for t in heute)
    teile = []
    for i, (titel, text, link) in enumerate(punkte):
        quelle = f'<p><a class="source-link" href="{link}">Weiterlesen bei der Presse →</a></p>' if link else ""
        teile.append(
            f"<h2>{titel}</h2>\n  <p><strong>Was ist neu:</strong> {text}</p>\n"
            f"  <p><strong>Warum es zählt:</strong> Folgen für dich. (Recht)</p>\n  {quelle}\n"
            f'<div class="article-fb" data-key="x|morgen|{i}"></div>'
        )
    return (
        f'<header class="lagebild-header"><h1>{h1}</h1></header>'
        f'<div class="highlights"><p><strong>Heute wichtig:</strong></p>{hl}</div><hr>'
        + "".join(teile)
        + f'<div class="done">Du bist informiert — Lesezeit ca. {lesezeit} Sekunden.</div>'
    )


SAUBER = [
    ("Gericht kippt Mietpreisdeckel", "Der VfGH hob den Mietpreisdeckel auf.",
     "https://www.diepresse.com/1/vfgh-kippt-mietpreisdeckel"),
    ("Lufthansa streicht 1000 Stellen", "Die Lufthansa baut 1000 Stellen ab.",
     "https://www.diepresse.com/2/lufthansa"),
]


def _pruefe(tmp_path, seite, datum=date(2026, 12, 1), zeit=(6, 2)):
    (tmp_path / f"{datum.isoformat()}-morgen.html").write_text(seite, encoding="utf-8")
    return pruefung.pruefe(datum, "morgen", CONFIG, archiv=tmp_path, commit_zeit=_um(datum, *zeit))


def test_saubere_ausgabe_ohne_befund(tmp_path):
    assert _pruefe(tmp_path, _seite(SAUBER)) == []


def test_fehlende_ausgabe(tmp_path):
    befunde = pruefung.pruefe(date(2026, 12, 1), "morgen", CONFIG, archiv=tmp_path)
    assert len(befunde) == 1 and "Ausgabe fehlt" in befunde[0]


def test_verspaetet_und_zu_frueh(tmp_path):
    assert "Verspätet" in _pruefe(tmp_path, _seite(SAUBER), zeit=(8, 15))[0]
    # 20.11.: Morgen-Ausgabe um 01:08 (verspäteter Abend-Cron)
    assert "Zu früh" in _pruefe(tmp_path, _seite(SAUBER), zeit=(1, 8))[0]


def test_fehlender_link_heute_wichtig_und_lesezeit(tmp_path):
    punkte = [SAUBER[0], ("Lufthansa streicht 1000 Stellen", "Die Lufthansa baut 1000 Stellen ab.", "")]
    befunde = _pruefe(tmp_path, _seite(punkte, heute=[SAUBER[0][0]], lesezeit=120))
    text = "\n".join(befunde)
    assert "Quell-Link fehlt bei Punkt 2" in text
    assert "„Heute wichtig“ (1 Zeilen) spiegelt die 2 Punkte nicht" in text
    assert "Lesezeit 120 s über dem Budget von 90 s" in text


def test_zahl_im_titel_und_schlagzeile(tmp_path):
    punkte = [("Wien muss 100 Millionen Euro sparen", "Die Kosten sind auf 1,1 Milliarden Euro gestiegen.",
               "https://www.diepresse.com/3/wien")]
    befunde = _pruefe(tmp_path, _seite(punkte, h1="Wien drosselt Mindestsicherung"))
    assert any("Zahl(en) 100" in b for b in befunde)
    assert any("H1: Wörter nicht in den Punkten (drosselt" in b for b in befunde)


def test_echte_ausgabe_vom_27_11(tmp_path):
    shutil.copy(ROOT / "site/archiv/2026-11-27-morgen.html", tmp_path / "2026-11-27-morgen.html")
    d = date(2026, 11, 27)
    befunde = pruefung.pruefe(d, "morgen", CONFIG, archiv=tmp_path, commit_zeit=_um(d, 6, 2))
    text = "\n".join(befunde)
    assert "„ab Montag“" in text and "1. Dezember" in text
    assert "Absicht im Text" in text


def test_presse_schlagzeile_ist_kein_absichts_befund(tmp_path):
    punkte = [("Spritpreisbremse: Hattmannsdorfer für Auslaufen des Margeneingriffs",
               "Wirtschaftsminister Hattmannsdorfer will die Margenbegrenzung auslaufen lassen.",
               "https://www.diepresse.com/41495014/spritpreisbremse-hattmannsdorfer-fuer-auslaufen-des-margeneingriffs")]
    seite = _seite(punkte, h1="Spritpreisbremse: Hattmannsdorfer für Auslaufen des Margeneingriffs")
    assert _pruefe(tmp_path, seite) == []


def test_ruhe_ausgabe_ohne_punkte_ist_ok(tmp_path):
    assert _pruefe(tmp_path, "<h1>Ruhige Lage</h1><p>Nichts Neues.</p>") == []


def test_bericht_enthaelt_auftrag():
    text = pruefung.bericht(date(2026, 12, 1), "morgen", ["Quell-Link fehlt bei Punkt 2."])
    assert "- Quell-Link fehlt bei Punkt 2." in text and "UEBERGABE.md" in text


def test_workflow_prueft_taeglich_und_meldet():
    wf = yaml.safe_load((ROOT / ".github/workflows/qualitaet.yml").read_text(encoding="utf-8"))
    triggers = wf.get("on") or wf.get(True)
    assert triggers["schedule"][0]["cron"] == "40 5 * * *"
    job = wf["jobs"]["pruefen"]
    assert job["permissions"] == {"contents": "read", "issues": "write"}
    runs = " ".join(str(s.get("run", "")) for s in job["steps"])
    assert "copilot.main pruefen" in runs and "labels[]=qualitaetscheck" in runs and "sendMessage" in runs
