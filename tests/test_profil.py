"""Wirkungs-Profil: Fragenlogik, Codes aus der PWA, Prompt-Block."""
import base64
import json

import pytest

from copilot import profil


def test_naechste_frage_folgt_der_reihenfolge():
    assert profil.naechste_frage({})["key"] == "wohnen"
    assert profil.naechste_frage({"wohnen": "miete"})["key"] == "kredit"


def test_kredithoehe_nur_bei_kredit():
    ohne = {"wohnen": "miete", "kredit": "keiner"}
    assert profil.naechste_frage(ohne)["key"] == "beruf"
    mit = {"wohnen": "miete", "kredit": "variabel"}
    assert profil.naechste_frage(mit)["key"] == "kredithoehe"


def test_antwort_speichern_prueft_werte():
    state = {}
    assert profil.antwort_speichern(state, "wohnen", "miete")
    assert not profil.antwort_speichern(state, "wohnen", "villa")
    assert not profil.antwort_speichern(state, "gibtsnicht", "x")
    assert profil.get_profil(state) == {"wohnen": "miete"}


def test_bedingte_antwort_wird_aufgeraeumt():
    state = {}
    profil.antwort_speichern(state, "kredit", "variabel")
    profil.antwort_speichern(state, "kredithoehe", "100_300")
    assert "kredithoehe" in profil.get_profil(state)
    profil.antwort_speichern(state, "kredit", "keiner")
    assert "kredithoehe" not in profil.get_profil(state)


def test_fortschritt_zaehlt_nur_zutreffende_fragen():
    beantwortet, gesamt = profil.fortschritt({"kredit": "keiner"})
    assert beantwortet == 1
    assert gesamt == len(profil.FRAGEN) - 1  # Kredithöhe entfällt


def test_code_uebernehmen_filtert_unbekanntes():
    payload = json.dumps({"wohnen": "miete", "kredit": "fix", "hack": "x", "beruf": "quatsch"})
    code = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    state = {}
    n = profil.code_uebernehmen(state, code)
    assert n == 2
    assert profil.get_profil(state) == {"wohnen": "miete", "kredit": "fix"}


def test_code_uebernehmen_lehnt_muell_ab():
    with pytest.raises(Exception):
        profil.code_uebernehmen({}, "keinbase64!!")


def test_prompt_block_nur_mit_profil():
    assert profil.prompt_block({}) == ""
    block = profil.prompt_block({"wohnen": "miete", "kredit": "variabel"})
    assert "wohnt zur Miete" in block
    assert "variabel verzinsten Kredit" in block
    # Der Block darf die Auswahl nicht steuern — nur die Einordnung.
    assert "niemals zur Auswahl" in block
    assert "Für dich konkret" in block


def test_prompt_block_englisch():
    block = profil.prompt_block({"wohnen": "miete"}, lang="en")
    assert "What it means for you" in block
    assert "never to select stories" in block


def test_profil_loeschen():
    state = {}
    profil.antwort_speichern(state, "wohnen", "miete")
    profil.profil_loeschen(state)
    assert profil.get_profil(state) == {}
