"""Optionaler Versand des Lagebilds per E-Mail (SMTP-Zugang aus .env)."""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))


def send_email(subject: str, markdown: str, html_body: str, recipients: list[str]) -> None:
    if not recipients:
        print("Keine Empfänger in config.yaml — Versand übersprungen.")
        return
    if not smtp_configured():
        print("SMTP nicht konfiguriert (.env) — Versand übersprungen.")
        return

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ["SMTP_FROM"]

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender
    message.attach(MIMEText(markdown, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        try:
            server.starttls()
            server.ehlo()
        except smtplib.SMTPNotSupportedError:
            pass
        if user and password:
            server.login(user, password)
        for recipient in recipients:
            del message["To"]
            message["To"] = recipient
            server.sendmail(sender, [recipient], message.as_string())
            print(f"Gesendet an {recipient}")
