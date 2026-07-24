"""Rückkanal: neue Button-Taps (Profil, gelesen, hat gefehlt)."""
import pytest

from copilot import rueckkanal


class FakeTelegram:
    """Minimaler Ersatz für das telegram-Modul — merkt sich, was rausgegangen wäre."""

    def __init__(self):
        self.callbacks = []
        self.alerts = []
        self.fragen = []

    def answer_callback(self, cq_id, text=""):
        self.callbacks.append(text)

    def send_alert(self, text, chat_ids):
        self.alerts.append(text)

    def send_question(self, text, chat_id, keyboard):
        self.fragen.append((text, keyboard))

    def profil_keyboard(self, frage):
        from copilot import telegram
        return telegram.profil_keyboard(frage)

    def confirm_feedback(self, *a, **kw):
        pass


@pytest.fixture
def tg():
    return FakeTelegram()


def _cq(data: str, chat_id: str = "42") -> dict:
    return {"id": "cq1", "data": data, "message": {"chat": {"id": chat_id}, "message_id": 7}}


def test_profil_tap_speichert_und_stellt_naechste_frage(tg):
    st: dict = {}
    n = rueckkanal._handle_callback(_cq("prof|wohnen|miete"), {"42"}, st, tg)
    assert n == 1
    assert st["profil"]["antworten"] == {"wohnen": "miete"}
    assert tg.fragen and "Frage 2 von" in tg.fragen[0][0]


def test_profil_tap_mit_unbekanntem_wert_wird_verworfen(tg):
    st: dict = {}
    assert rueckkanal._handle_callback(_cq("prof|wohnen|villa"), {"42"}, st, tg) == 0
    assert "profil" not in st


def test_lese_tap_wird_notiert(tg):
    st: dict = {}
    assert rueckkanal._handle_callback(_cq("read|2026-07-24|abend"), {"42"}, st, tg) == 1
    assert st["read_events"][0]["quelle"] == "telegram_tap"
    assert "Tag in Folge" in tg.callbacks[0]


def test_fehlt_tap_erklaert_den_befehl(tg):
    st: dict = {}
    assert rueckkanal._handle_callback(_cq("fehlt|2026-07-24|abend"), {"42"}, st, tg) == 0
    assert any("/fehlt" in a for a in tg.alerts)


def test_artikel_feedback_zaehlt_als_lese_signal(tg):
    st = {"edition_points": {"2026-07-24|abend": ["Ein Punkt"]}}
    rueckkanal._handle_callback(_cq("artfb|2026-07-24|abend|0|up"), {"42"}, st, tg)
    assert st["article_feedback"][0]["rating"] == "up"
    assert st["read_events"][0]["quelle"] == "artfb"


def test_ausgaben_feedback_zaehlt_als_lese_signal(tg):
    st: dict = {}
    rueckkanal._handle_callback(_cq("fb|2026-07-24|abend|up"), {"42"}, st, tg)
    assert st["feedback"][0]["rating"] == "up"
    assert st["read_events"][0]["quelle"] == "fb"


def test_fremde_chat_id_wird_ignoriert(tg):
    st: dict = {}
    assert rueckkanal._handle_callback(_cq("read|2026-07-24|abend", "999"), {"42"}, st, tg) == 0
    assert "read_events" not in st


def test_frage_stellen_meldet_fertiges_profil(tg):
    from copilot import profil
    antworten = {f["key"]: f["optionen"][0][0] for f in profil.FRAGEN}
    st = {"profil": {"antworten": antworten}}
    rueckkanal._frage_stellen(st, "42", tg)
    assert tg.fragen == []
    assert any("Wirkungs-Profil steht" in a for a in tg.alerts)
