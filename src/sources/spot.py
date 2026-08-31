"""
International spot price, converted to INR — NOT used as a displayed rate
(it runs ~15% below Delhi retail because it excludes import duty, GST, and
local premium). Its only job is to compute india_premium = delhi_24k / spot_24k
as a correctness canary: if that ratio suddenly jumps, a Delhi scraper likely
broke rather than gold actually moving.
"""
from __future__ import annotations

from datetime import date
from typing import Optional, TypedDict

import requests

from src import config

URL = "https://api.goldprice.dev/v1/carat?currency=INR"


class SpotRecord(TypedDict):
    source: str
    date: str
    spot_24k: float
    spot_22k: float
    spot_18k: float


def fetch_spot() -> Optional[SpotRecord]:
    try:
        resp = requests.get(URL, timeout=config.HTTP_TIMEOUT_SECONDS)
        resp.raise_for_status()
        data = resp.json()
        return {
            "source": "goldprice.dev",
            "date": date.today().isoformat(),
            "spot_24k": float(data["price_gram_24k"]),
            "spot_22k": float(data["price_gram_22k"]),
            "spot_18k": float(data["price_gram_18k"]),
        }
    except (requests.RequestException, KeyError, ValueError) as exc:
        print(f"[spot] fetch failed: {exc}")
        return None


if __name__ == "__main__":
    print(fetch_spot())
