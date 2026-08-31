"""Notifier interface — tracker.py sends to every enabled notifier without
caring which channel it is. Adding a new channel later is one class here
plus one line in config.py; no orchestrator change needed."""
from __future__ import annotations

import abc


class Notifier(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def send(self, text: str) -> bool:
        """Send `text`. Return True on success, False on failure — never raise,
        so one broken channel can't take down the whole run."""
        raise NotImplementedError
