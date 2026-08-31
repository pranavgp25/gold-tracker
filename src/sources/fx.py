"""USD/INR rate — used as a signal feature (a weakening rupee lifts local
gold even when global spot is flat) and for context in the digest."""
from __future__ import annotations

from typing import Optional

import requests

from src import config

URL = "https://api.frankfurter.dev/v1/latest?base=USD&symbols=INR"


def fetch_usd_inr() -> Optional[float]:
    try:
        resp = requests.get(URL, timeout=config.HTTP_TIMEOUT_SECONDS)
        resp.raise_for_status()
        data = resp.json()
        return float(data["rates"]["INR"])
    except (requests.RequestException, KeyError, ValueError) as exc:
        print(f"[fx] fetch failed: {exc}")
        return None


if __name__ == "__main__":
    print(fetch_usd_inr())
