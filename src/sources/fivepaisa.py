"""
Cross-check source, and a secondary backfill source. 5paisa dates its page
correctly (verified against the current day, unlike business-standard.com
which was found serving a page stale by ~3 months) and phrases its rate
sentence the same way goodreturns does, so it reuses the shared
extract_karat_rate anchor. 18K is present on this page too, but its 18K
figure diverges ~14% from goodreturns' (vs a normal ~2% cross-source spread
for 24K/22K) — likely a different pricing formula on their end — so we
deliberately do NOT use it; 18K stays goodreturns-only per the primary
source's design.

5paisa's own "today" figure lags goodreturns' by up to a day around a rate
revision (observed: showing the prior day's close for part of a day), so its
*current* fetch() should never override goodreturns as the display headline.
Its *historical* backfill_10day() table is still useful, though: goodreturns'
own "Last 10 Days" table has gaps (skips some calendar days entirely — see
goodreturns.py), while 5paisa's table is a dense, gap-free run of 10
consecutive calendar days. tracker.py uses it only to fill dates goodreturns'
table is missing, never to overwrite a date goodreturns already covers.
"""
from __future__ import annotations

import re
from datetime import date
from typing import List, Optional, TypedDict

from src.sources.base import Source, RateRecord
from src.sources._html import flatten, extract_karat_rate

URL = "https://www.5paisa.com/commodity-trading/gold/delhi"


class BackfillRow(TypedDict):
    date: str
    k24: float
    k22: float


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

    def backfill_10day(self) -> List[BackfillRow]:
        """Parse the dd-mm-yyyy dated 10-day table. Values there are per-10g;
        divided by 10 here so the schema matches goodreturns' per-gram figures."""
        raw = self.fetch_html(URL)
        if raw is None:
            return []
        text = flatten(raw)

        row_pattern = re.compile(
            r"(\d{2})-(\d{2})-(\d{4})\s+([\d,]+)\s+[+-]?[\d,]+\s*\([+-]?[\d.]+%\)\s+"
            r"([\d,]+)\s+[+-]?[\d,]+\s*\([+-]?[\d.]+%\)"
        )

        rows: List[BackfillRow] = []
        for dd, mm, yyyy, p24_10g, p22_10g in row_pattern.findall(text):
            iso = date(int(yyyy), int(mm), int(dd)).isoformat()
            rows.append(
                {
                    "date": iso,
                    "k24": round(float(p24_10g.replace(",", "")) / 10, 2),
                    "k22": round(float(p22_10g.replace(",", "")) / 10, 2),
                }
            )
        if not rows:
            print(f"[{self.name}] backfill table not found — layout may have changed")
        return rows


if __name__ == "__main__":
    print(FivePaisaSource().fetch())
    print(FivePaisaSource().backfill_10day())
