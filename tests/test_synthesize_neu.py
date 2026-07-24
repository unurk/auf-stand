"""Prompt-Erweiterungen: Profil-Block, Kalibrierung, Vollständigkeits-Abschnitt."""
from copilot import synthesize
from copilot.fetch import Article


def _artikel():
    return [Article(id="1", title="Titel", teaser="Teaser", link="https://x.at",
                    ressort="Politik", published=None)]


def test_prompt_enthaelt_pruef_abschnitt():
    prompt = synthesize.build_prompt(_artikel(), [], "Abend-Ausgabe")
    assert "Geprüft, nicht aufgenommen" in prompt
    assert "{NICHT_AUFGENOMMEN_SECTION}" not in prompt


def test_prompt_mit_profil():
    prompt = synthesize.build_prompt(
        _artikel(), [], "Abend-Ausgabe", profil={"wohnen": "miete", "kredit": "variabel"}
    )
    assert "Wirkungs-Profil" in prompt
    assert "wohnt zur Miete" in prompt


def test_prompt_ohne_profil_bleibt_schlank():
    prompt = synthesize.build_prompt(_artikel(), [], "Abend-Ausgabe", profil={})
    assert "Wirkungs-Profil" not in prompt


def test_kalibrierung_buendelt_alle_hinweise():
    prompt = synthesize.build_prompt(
        _artikel(), [], "Abend-Ausgabe",
        article_feedback_hint="A-Hinweis\n",
        missing_hint="M-Hinweis\n",
        budget_hint="B-Hinweis\n",
    )
    block = prompt.split("# Kalibrierung")[1].split("# Material")[0]
    assert "A-Hinweis" in block and "M-Hinweis" in block and "B-Hinweis" in block


def test_keine_kalibrierung_ohne_hinweise():
    prompt = synthesize.build_prompt(_artikel(), [], "Abend-Ausgabe")
    assert "# Kalibrierung" not in prompt


def test_prompt_englisch_nutzt_englische_bausteine():
    prompt = synthesize.build_prompt(
        _artikel(), [], "Evening Briefing", lang="en",
        prompt_file="lagebild.en.md", profil={"wohnen": "miete"},
    )
    assert "Checked, not included" in prompt
    assert "Reader profile" in prompt


def test_quiz_ohne_provider_leer(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    assert synthesize.generate_quiz(["Punkt A", "Punkt B"], {}) == []


def test_quiz_filtert_kaputte_fragen(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    antwort = """[
      {"frage": "Wer?", "optionen": ["a", "b", "c"], "richtig": 1, "erklaerung": "weil"},
      {"frage": "Ohne Optionen", "optionen": [], "richtig": 0},
      {"frage": "Index daneben", "optionen": ["a", "b"], "richtig": 7},
      {"optionen": ["a", "b"], "richtig": 0}
    ]"""
    monkeypatch.setattr(synthesize, "_complete", lambda *a, **kw: antwort)
    fragen = synthesize.generate_quiz(["Punkt A"], {"provider": "anthropic"})
    assert len(fragen) == 1
    assert fragen[0]["frage"] == "Wer?"
    assert fragen[0]["richtig"] == 1
