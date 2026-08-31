"""
Combines the primary (goodreturns) record with cross-check sources into one
reconciled record for storage.

Design rules (see plan Context #1 and #2):
- The DISPLAYED headline rate and every signal input come from goodreturns
  alone — it is the only source with all three karats, and mixing sources'
  own day-over-day deltas would manufacture fake moves (sources disagree by
  up to ~2% on any given day).
- Cross-check sources exist only to catch a broken primary scraper: if
  goodreturns drifts far from the cross-check median, we flag it rather than
  silently trusting a possibly-broken parse.
- If the primary source fails entirely, the caller (tracker.py) carries the
  previous record forward with stale=True. This module never invents a price.
"""
from __future__ import annotations

import statistics
from datetime import date
from typing import List, Optional, TypedDict

from src import config
from src.sources.base import RateRecord


class ReconciledRecord(TypedDict, total=False):
    date: str
    k24: float
    k22: float
    k18: Optional[float]
    primary_source: str
    cross_check_median_24: Optional[float]
    spread_pct: Optional[float]          # (max-min)/median across all sources that answered
    outlier_sources: List[str]
    india_premium: Optional[float]       # delhi_24k / international spot_24k
    usd_inr: Optional[float]
    stale: bool


def reconcile(
    primary: RateRecord,
    cross_checks: List[RateRecord],
    spot_24k: Optional[float],
    usd_inr: Optional[float],
) -> ReconciledRecord:
    if "k24" not in primary or "k22" not in primary:
        raise ValueError("primary record must carry k24 and k22")

    all_24 = [primary["k24"]] + [c["k24"] for c in cross_checks if "k24" in c]
    outliers = []
    for c in cross_checks:
        if "k24" not in c:
            continue
        deviation = abs(c["k24"] - primary["k24"]) / primary["k24"]
        if deviation > config.OUTLIER_REJECT_PCT:
            outliers.append(c["source"])

    cross_24_values = [c["k24"] for c in cross_checks if "k24" in c and c["source"] not in outliers]
    cross_check_median_24 = statistics.median(cross_24_values) if cross_24_values else None

    usable_24 = [v for v in all_24]
    spread_pct = None
    if len(usable_24) >= 2:
        spread_pct = round((max(usable_24) - min(usable_24)) / statistics.median(usable_24) * 100, 3)

    india_premium = None
    if spot_24k:
        india_premium = round(primary["k24"] / spot_24k, 4)

    record: ReconciledRecord = {
        "date": primary.get("date", date.today().isoformat()),
        "k24": primary["k24"],
        "k22": primary["k22"],
        "k18": primary.get("k18"),
        "primary_source": primary["source"],
        "cross_check_median_24": cross_check_median_24,
        "spread_pct": spread_pct,
        "outlier_sources": outliers,
        "india_premium": india_premium,
        "usd_inr": usd_inr,
        "stale": False,
    }

    if outliers:
        print(f"[reconcile] outlier source(s) vs primary (>{config.OUTLIER_REJECT_PCT*100:.0f}%): {outliers}")

    return record
