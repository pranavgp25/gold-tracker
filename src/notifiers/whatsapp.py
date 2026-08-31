"""
WhatsApp notifier — NOT implemented in V1.

Why: business-initiated WhatsApp alerts require a Meta-approved *utility
message template* and are billed per message once outside the free 24-hour
customer-service window; Meta is retiring that free window in October 2026.
The Twilio sandbox alternative requires rejoining every 72 hours, which is
unworkable for a standing daily alert. Telegram has none of these constraints
and is free and unlimited, so it is the V1 channel (see telegram.py).

To add WhatsApp later:
1. Get a Meta Business + WhatsApp Cloud API account and an approved utility
   template for the daily digest.
2. Implement send() below using the Cloud API's /messages endpoint, reading
   WHATSAPP_TOKEN / WHATSAPP_PHONE_ID from env (never hardcoded — see
   security rules in the repo owner's global config).
3. Register an instance in build_notifiers() in src/tracker.py — the rest of
   tracker.py requires no change, since it iterates that list generically.
"""
from __future__ import annotations

from src.notifiers.base import Notifier


class WhatsAppNotifier(Notifier):
    name = "whatsapp"

    def send(self, text: str) -> bool:
        raise NotImplementedError(
            "WhatsApp notifier is a documented stub for V1 — see module docstring. "
            "Use TelegramNotifier for now."
        )
