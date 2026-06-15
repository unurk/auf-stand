"""Optionaler Web-Push-Versand an PWA-Abonnenten (VAPID, Keys aus .env).

Subscriptions kommen über den Telegram-Rückkanal (/push) herein und liegen in
state["push_subscriptions"]. Der Versand läuft in der GitHub-Actions-Pipeline —
GitHub Pages selbst ist statisch und kann nichts senden.
"""
from __future__ import annotations

import base64
import json
import os


def webpush_configured() -> bool:
    return bool(
        os.environ.get("VAPID_PRIVATE_KEY")
        and os.environ.get("VAPID_PUBLIC_KEY")
        and os.environ.get("VAPID_SUBJECT")
    )


def generate_vapid_keys() -> tuple[str, str]:
    """Erzeugt ein VAPID-Schlüsselpaar (public, private) als base64url-Strings."""
    from py_vapid import Vapid01
    from cryptography.hazmat.primitives import serialization

    v = Vapid01()
    v.generate_keys()
    raw_pub = v.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    raw_priv = v.private_key.private_numbers().private_value.to_bytes(32, "big")
    pub = base64.urlsafe_b64encode(raw_pub).decode().rstrip("=")
    priv = base64.urlsafe_b64encode(raw_priv).decode().rstrip("=")
    return pub, priv


def send_push(title: str, body: str, url: str, state: dict, config: dict) -> int:
    """Sendet eine Notification an alle gespeicherten Subscriptions.

    Entfernt abgemeldete/abgelaufene Subscriptions (HTTP 404/410) aus dem State.
    Gibt die Anzahl erfolgreich zugestellter Pushes zurück.
    """
    subscriptions = state.get("push_subscriptions", [])
    if not subscriptions:
        print("Keine Push-Abonnenten — Web-Push übersprungen.")
        return 0
    if not webpush_configured():
        print("VAPID nicht konfiguriert (.env) — Web-Push übersprungen.")
        return 0

    from pywebpush import webpush, WebPushException
    from . import state as state_module

    private_key = os.environ["VAPID_PRIVATE_KEY"]
    claims = {"sub": os.environ["VAPID_SUBJECT"]}
    payload = json.dumps({"title": title, "body": body, "url": url})

    sent = 0
    stale: list[str] = []
    for sub in subscriptions:
        endpoint = sub.get("endpoint", "")
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=private_key,
                vapid_claims=dict(claims),  # webpush mutiert die Claims (exp), Kopie geben
            )
            sent += 1
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410):
                stale.append(endpoint)
                print(f"Push-Abo abgelaufen (HTTP {status}) — entfernt.")
            else:
                print(f"Web-Push Fehler ({status}): {exc}")
        except Exception as exc:
            print(f"Web-Push Fehler: {exc}")

    if stale:
        for endpoint in stale:
            state_module.remove_push_subscription(state, endpoint)
        state_module.save_state(state)

    print(f"Web-Push: {sent}/{len(subscriptions)} zugestellt.")
    return sent
