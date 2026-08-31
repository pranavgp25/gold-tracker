"""Shared HTML-mining helpers used by multiple scrapers."""
from __future__ import annotations

import html
import re
from typing import Optional


def flatten(raw_html: str) -> str:
    """Unescape entities, strip tags, collapse whitespace -> searchable text blob."""
    unescaped = html.unescape(raw_html)
    no_tags = re.sub(r"<[^>]+>", " ", unescaped)
    return re.sub(r"\s+", " ", no_tags)


def extract_karat_rate(text: str, karat: int) -> Optional[float]:
    """
    Anchor on the karat word itself (not position), so a source reordering the
    sentence can't silently mis-assign a price to the wrong karat. Matches the
    common "₹X per gram for N karat" phrasing used by several rate sites.
    """
    m = re.search(
        rf"₹\s*([\d,]+)\s*per\s+gram\s+for\s+{karat}\s*karat",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return float(m.group(1).replace(",", ""))
