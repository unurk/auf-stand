"""OAuth 2.0 Authentifizierung für die WHOOP Developer API."""
from __future__ import annotations

import json
import os
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
TOKEN_FILE = BASE_DIR / "data" / "tokens.json"

_AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
REDIRECT_URI = "http://localhost:8765/callback"
SCOPES = "read:cycles read:recovery read:sleep read:workout read:body offline"


def _load_tokens() -> dict:
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    return {}


def _save_tokens(tokens: dict) -> None:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


def _exchange(data: dict) -> dict:
    client_id = os.environ["WHOOP_CLIENT_ID"]
    client_secret = os.environ["WHOOP_CLIENT_SECRET"]
    resp = requests.post(
        _TOKEN_URL,
        data=data,
        auth=(client_id, client_secret),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_valid_token() -> str:
    """Gibt einen gültigen Access-Token zurück — refresht automatisch wenn nötig."""
    if not os.environ.get("WHOOP_CLIENT_ID") or not os.environ.get("WHOOP_CLIENT_SECRET"):
        raise SystemExit(
            "WHOOP_CLIENT_ID und WHOOP_CLIENT_SECRET fehlen.\n"
            "1. App auf developer.whoop.com registrieren\n"
            "2. Redirect URI eintragen: http://localhost:8765/callback\n"
            "3. Credentials in .env hinterlegen"
        )

    tokens = _load_tokens()
    if not tokens.get("access_token"):
        raise SystemExit(
            "Noch nicht verbunden. Zuerst ausführen:\n  python -m whoop.main auth"
        )

    if tokens.get("expires_at", 0) > time.time() + 60:
        return tokens["access_token"]

    if not tokens.get("refresh_token"):
        raise SystemExit(
            "Session abgelaufen. Erneut verbinden:\n  python -m whoop.main auth"
        )

    refreshed = _exchange(
        {"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"]}
    )
    tokens["access_token"] = refreshed["access_token"]
    tokens["refresh_token"] = refreshed.get("refresh_token", tokens["refresh_token"])
    tokens["expires_at"] = time.time() + refreshed.get("expires_in", 3600)
    _save_tokens(tokens)
    return tokens["access_token"]


def run_auth_flow() -> None:
    """OAuth-Flow: Browser öffnen, Callback abfangen, Tokens speichern."""
    if not os.environ.get("WHOOP_CLIENT_ID") or not os.environ.get("WHOOP_CLIENT_SECRET"):
        raise SystemExit(
            "WHOOP_CLIENT_ID und WHOOP_CLIENT_SECRET fehlen — zuerst in .env eintragen."
        )

    state = secrets.token_urlsafe(16)
    auth_url = _AUTH_URL + "?" + urlencode(
        {
            "response_type": "code",
            "client_id": os.environ["WHOOP_CLIENT_ID"],
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "state": state,
        }
    )

    received_code: list[str] = []

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # noqa: ANN001
            pass

        def do_GET(self):  # noqa: N802
            qs = parse_qs(urlparse(self.path).query)
            if qs.get("state", [""])[0] != state or not qs.get("code"):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Fehler: Ungueltige Antwort.")
                return
            received_code.append(qs["code"][0])
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>Verbunden!</h2>"
                b"<p>Dieses Fenster kann geschlossen werden.</p></body></html>"
            )

    print(f"Browser wird geöffnet …\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8765), _Handler)
    server.handle_request()
    server.server_close()

    if not received_code:
        raise SystemExit("Kein Autorisierungscode empfangen.")

    token_data = _exchange(
        {
            "grant_type": "authorization_code",
            "code": received_code[0],
            "redirect_uri": REDIRECT_URI,
        }
    )
    _save_tokens(
        {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", ""),
            "expires_at": time.time() + token_data.get("expires_in", 3600),
        }
    )
    print("WHOOP verbunden. Tokens gespeichert in data/tokens.json")
