"""
PRIMARY source. goodreturns.in is the only site that publishes all three karats
(24K/22K/18K) we track, and it also ships a "Last 10 Days" table (24K/22K only,
with the day-over-day change already computed) that we use once to backfill
history on a cold start.

Because sources disagree by ~2% on any given day, this project's own daily
history.json series (not goodreturns' printed delta) is the source of truth for
"today vs yesterday" once we have 2+ days of our own data. The printed deltas
are only used to seed the first 10 days.
"""
from __future__ import annotations

import re
from datetime import date
from typing import List, Optional, TypedDict

from src.sources.base import Source, RateRecord
from src.sources._html import flatten, extract_karat_rate

URL = "https://www.goodreturns.in/gold-rates/delhi.html"

_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


class BackfillRow(TypedDict):
    date: str
    k24: float
    k22: float
    change_24: float
    change_22: float


class GoodReturnsSource(Source):
    name = "goodreturns"

    def fetch(self) -> Optional[RateRecord]:
        raw = self.fetch_html(URL)
        if raw is None:
            return None
        text = flatten(raw)

        k24 = extract_karat_rate(text, 24)
        k22 = extract_karat_rate(text, 22)
        k18 = extract_karat_rate(text, 18)

        if k24 is None or k22 is None:
            print(f"[{self.name}] could not find 24K/22K in page — layout may have changed")
            return None
        if k18 is None:
            print(f"[{self.name}] could not find 18K — leaving it out of this record")

        record: RateRecord = {
            "source": self.name,
            "date": date.today().isoformat(),
            "k24": k24,
            "k22": k22,
        }
        if k18 is not None:
            record["k18"] = k18
        return record

    def backfill_10day(self) -> List[BackfillRow]:
        """
        Parse the "Last 10 Days" table. Returns newest-first (matches page order).
        Only 24K/22K are available historically from this table; 18K history
        accumulates from our own daily scrapes going forward.
        """
        raw = self.fetch_html(URL)
        if raw is None:
            return []
        text = flatten(raw)

        row_pattern = re.compile(
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),\s+(\d{4})\s+"
            r"₹\s*([\d,]+)\s*\(([-\d]+)\)\s+"
            r"₹\s*([\d,]+)\s*\(([-\d]+)\)"
        )

        rows: List[BackfillRow] = []
        for mon, day, year, p24, chg24, p22, chg22 in row_pattern.findall(text):
            iso = date(int(year), _MONTHS[mon], int(day)).isoformat()
            rows.append(
                {
                    "date": iso,
                    "k24": float(p24.replace(",", "")),
                    "k22": float(p22.replace(",", "")),
                    "change_24": float(chg24),
                    "change_22": float(chg22),
                }
            )
        if not rows:
            print(f"[{self.name}] backfill table not found — layout may have changed")
        return rows


if __name__ == "__main__":
    src = GoodReturnsSource()
    print("current:", src.fetch())
    print("backfill:", src.backfill_10day())
