"""Tests für synthesize: Prompt-Bau und Provider-Dispatch (anthropic | glm)."""
from datetime import datetime, timezone

import httpx
import pytest

from copilot import synthesize
from copilot.fetch import Article


def _art() -> Article:
    return Article(
        "a1", "EZB senkt Leitzins", "Die EZB reagiert.", "https://x/a1", "Wirtschaft",
        datetime(2026, 7, 4, 10, 0, tzinfo=timezone.utc), author="Max Mustermann",
    )


def test_build_prompt_ersetzt_platzhalter_und_listet_material():
    prompt = synthesize.build_prompt(
        [_art()],
        [{"name": "EZB-Zinsen", "schlagwort": "EZB"}],
        "Morgen-Ausgabe",
        next_edition="Nächste Ausgabe heute 11:00.",
        edition_emoji="☀️",
    )
    # Kein Platzhalter übrig
    for placeholder in ("{EDITION_EMOJI}", "{DATUM_LABEL}", "{LESEZEIT}", "{NAECHSTE_AUSGABE}"):
        assert placeholder not in prompt
    assert "☀️" in prompt
    assert "[Wirtschaft] EZB senkt Leitzins" in prompt
    assert "Max Mustermann" in prompt
    assert "https://x/a1" in prompt
    assert "- EZB-Zinsen" in prompt


def test_topic_helpers():
    assert synthesize.topic_name({"name": "EZB", "schlagwort": "Zins"}) == "EZB"
    assert synthesize.topic_name("EZB-Zinsen") == "EZB-Zinsen"
    assert synthesize.topic_keyword({"name": "EZB", "schlagwort": "Zins"}) == "Zins"
    # Fallback: erstes Wort des Namens
    assert synthesize.topic_keyword("Mietrecht und Wohnkosten") == "Mietrecht"


def test_glm_provider_wird_genutzt(monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "test-key")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    calls = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        calls["url"] = url
        calls["model"] = json["model"]
        calls["auth"] = headers["Authorization"]
        calls["reasoning"] = json["reasoning"]
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "Das Lagebild."}}]}
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    config = {"provider": "glm", "glm": {"model": "z-ai/glm-5.2", "base_url": "https://openrouter.ai/api/v1"}}
    assert synthesize.synthesize("prompt", config) == "Das Lagebild."
    assert calls["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert calls["model"] == "z-ai/glm-5.2"
    assert calls["auth"] == "Bearer test-key"
    # Reasoning aus: sonst frisst das Denken das max_tokens-Budget und die
    # Antwort kommt mit finish_reason=length ohne Inhalt zurück.
    assert calls["reasoning"] == {"enabled": False}


def test_glm_leere_antwort_ist_transient(monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "test-key")

    def fake_post(url, headers=None, json=None, timeout=None):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": ""}, "finish_reason": "length"}]},
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(synthesize._TransientError, match="ohne Inhalt"):
        synthesize._complete_glm("prompt", {"provider": "glm"}, 100)


def test_glm_ohne_key_bricht_ab(monkeypatch):
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        synthesize.synthesize("prompt", {"provider": "glm"})


def test_transiente_fehler_werden_wiederholt(monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "test-key")
    monkeypatch.setattr("time.sleep", lambda s: None)
    attempts = []

    def flaky(prompt, config, max_tokens):
        attempts.append(1)
        if len(attempts) < 3:
            raise synthesize._TransientError("HTTP 529")
        return "ok"

    monkeypatch.setattr(synthesize, "_complete_glm", flaky)
    assert synthesize._complete("p", {"provider": "glm"}, 100) == "ok"
    assert len(attempts) == 3


def test_dauerhafter_transienter_fehler_gibt_auf(monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "test-key")
    monkeypatch.setattr("time.sleep", lambda s: None)

    def always_broken(prompt, config, max_tokens):
        raise synthesize._TransientError("HTTP 529")

    monkeypatch.setattr(synthesize, "_complete_glm", always_broken)
    with pytest.raises(RuntimeError, match="3 Versuchen"):
        synthesize._complete("p", {"provider": "glm"}, 100)


def test_provider_configured():
    import os
    assert synthesize._provider_configured({"provider": "glm"}) == bool(os.environ.get("ZAI_API_KEY"))
