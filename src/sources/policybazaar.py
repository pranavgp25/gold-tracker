"""
Cross-check source (24K/22K only — no 18K on this page). Used purely for
reconciliation/outlier detection against the primary goodreturns record;
never the displayed headline.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from src.sources.base import Source, RateRecord
from src.sources._html import flatten

URL = "https://www.policybazaar.com/gold-rate/delhi/"


class PolicyBazaarSource(Source):
    name = "policybazaar"

    def fetch(self) -> Optional[RateRecord]:
        raw = self.fetch_html(URL)
        if raw is None:
            return None
        text = flatten(raw)

        # The page renders a "24K 22K Live" tab header, then a "1 Gram ₹today ₹yesterday"
        # row for 24K immediately followed by the same shape for 22K.
        anchor = re.search(r"24K\s*22K\s*Live", text, re.IGNORECASE)
        if not anchor:
            print(f"[{self.name}] could not find karat table anchor — layout may have changed")
            return None

        row_pattern = re.compile(r"1\s*Gram\s*₹\s*([\d,]+)\s*₹\s*([\d,]+)")
        matches = list(row_pattern.finditer(text, anchor.end()))
        if len(matches) < 2:
            print(f"[{self.name}] expected 2 karat rows, found {len(matches)}")
            return None

        k24 = float(matches[0].group(1).replace(",", ""))
        k22 = float(matches[1].group(1).replace(",", ""))

        return {
            "source": self.name,
            "date": date.today().isoformat(),
            "k24": k24,
            "k22": k22,
        }


if __name__ == "__main__":
    print(PolicyBazaarSource().fetch())
