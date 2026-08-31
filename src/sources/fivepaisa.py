"""
Cross-check source. 5paisa dates its page correctly (verified against the
current day, unlike business-standard.com which was found serving a page
stale by ~3 months) and phrases its rate sentence the same way goodreturns
does, so it reuses the shared extract_karat_rate anchor. 18K is present on
this page too, but its 18K figure diverges ~14% from goodreturns' (vs a
normal ~2% cross-source spread for 24K/22K) — likely a different pricing
formula on their end — so we deliberately do NOT use it; 18K stays
goodreturns-only per the primary source's design.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from src.sources.base import Source, RateRecord
from src.sources._html import flatten, extract_karat_rate

URL = "https://www.5paisa.com/commodity-trading/gold/delhi"


class FivePaisaSource(Source):
    name = "fivepaisa"

    def fetch(self) -> Optional[RateRecord]:
        raw = self.fetch_html(URL)
        if raw is None:
            return None
        text = flatten(raw)

        k24 = extract_karat_rate(text, 24)
        k22 = extract_karat_rate(text, 22)

        if k24 is None or k22 is None:
            print(f"[{self.name}] could not find 24K/22K in page — layout may have changed")
            return None

        return {
            "source": self.name,
            "date": date.today().isoformat(),
            "k24": k24,
            "k22": k22,
        }


if __name__ == "__main__":
    print(FivePaisaSource().fetch())
