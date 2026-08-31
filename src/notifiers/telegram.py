"""
Telegram notifier — the V1 alert channel. Free, unlimited, no message-template
approval process (unlike WhatsApp business-initiated messages), so it is the
right default for a personal daily digest + occasional dip alert.

Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID as environment variables.
Set up once via @BotFather (token) and by messaging the bot then reading
https://api.telegram.org/bot<TOKEN>/getUpdates (chat id). See README.md.
"""
from __future__ import annotations

import os

import requests

from src import config
from src.notifiers.base import Notifier

API_URL = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier(Notifier):
    name = "telegram"

    def __init__(self) -> None:
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, text: str) -> bool:
        if not self.is_configured():
            print(
                "[telegram] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set — "
                r"add them to C:\credentials\.env locally or GitHub Actions Secrets "
                "in CI. Skipping send."
            )
            return False
        try:
            resp = requests.post(
                API_URL.format(token=self.token),
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"},
                timeout=config.HTTP_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            print("[telegram] sent: ok")
            return True
        except requests.RequestException as exc:
            # Never print the token; requests' URL in exceptions already excludes
            # it since it's in the path, not a header — but be explicit anyway.
            print(f"[telegram] send failed: {type(exc).__name__}")
            return False
