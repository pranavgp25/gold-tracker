"""
Source interface. Every source returns a normalised dict or None on failure —
a failing source must never crash the run (tracker.py treats None as "skip").
"""
from __future__ import annotations

import abc
from typing import Optional, TypedDict

import requests

from src import config


class RateRecord(TypedDict, total=False):
    source: str
    date: str          # ISO yyyy-mm-dd, IST
    k24: float
    k22: float
    k18: float
    change_24: float   # absolute daily change if the source publishes one, else omitted


class Source(abc.ABC):
    name: str = "base"

    def fetch_html(self, url: str) -> Optional[str]:
        """Shared fetch helper: timeout + UA + no raise on failure."""
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": config.USER_AGENT},
                timeout=config.HTTP_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            print(f"[{self.name}] fetch failed: {exc}")
            return None

    @abc.abstractmethod
    def fetch(self) -> Optional[RateRecord]:
        """Return today's rates, or None if the source could not be read."""
        raise NotImplementedError
