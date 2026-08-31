"""
Deterministic buy/wait signal engine. Pure functions over the 24K goodreturns
series stored in history.json — no I/O, no LLM, no external calls, so this
module is fully unit-testable and its output is reproducible run to run.

Verdict ladder (first match wins) — see config.SIGNAL for the thresholds:
  STRONG BUY  — near the 30-day floor AND below the 30-day average
  BUY         — a real single-day dip (not a bounce in an uptrend)
  ACCUMULATE  — below the 30-day average, but not an extreme
  WAIT        — near the 30-day ceiling, or well above the 30-day average
  HOLD        — none of the above (mid-range, no strong signal either way)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from src import config


class Features(TypedDict):
    price: float
    sma7: Optional[float]
    sma30: Optional[float]
    pos30: Optional[float]        # 0 = at the 30-day low, 1 = at the 30-day high
    drawdown_pct: Optional[float]  # % fall from the 30-day high
    down_streak: int
    d1_pct: Optional[float]
    d3_pct: Optional[float]
    inr_d1_pct: Optional[float]
    is_new_30day_low: bool
    window_size: int


class Signal(TypedDict):
    verdict: str
    reasons: List[str]
    confidence: str  # "full" | "low"
    features: Features


def _sma(values: List[float]) -> Optional[float]:
    return round(sum(values) / len(values), 2) if values else None


def compute_features(history: List[Dict[str, Any]]) -> Features:
    """`history` must be sorted ascending by date and each record have k24."""
    if not history:
        raise ValueError("history is empty — cannot compute features")

    prices = [r["k24"] for r in history if r.get("k24") is not None]
    if not prices:
        raise ValueError("no k24 values found in history")

    price = prices[-1]
    window30 = prices[-30:]
    window7 = prices[-7:]

    sma7 = _sma(window7)
    sma30 = _sma(window30)

    lo30, hi30 = min(window30), max(window30)
    pos30 = round((price - lo30) / (hi30 - lo30), 4) if hi30 > lo30 else 0.5
    drawdown_pct = round((hi30 - price) / hi30 * 100, 3) if hi30 > 0 else None

    down_streak = 0
    for i in range(len(prices) - 1, 0, -1):
        if prices[i] < prices[i - 1]:
            down_streak += 1
        else:
            break

    d1_pct = None
    if len(prices) >= 2 and prices[-2]:
        d1_pct = round((prices[-1] - prices[-2]) / prices[-2] * 100, 3)

    d3_pct = None
    if len(prices) >= 4 and prices[-4]:
        d3_pct = round((prices[-1] - prices[-4]) / prices[-4] * 100, 3)

    inr_rates = [r["usd_inr"] for r in history if r.get("usd_inr") is not None]
    inr_d1_pct = None
    if len(inr_rates) >= 2 and inr_rates[-2]:
        inr_d1_pct = round((inr_rates[-1] - inr_rates[-2]) / inr_rates[-2] * 100, 3)

    prior_low = min(window30[:-1]) if len(window30) > 1 else None
    is_new_30day_low = prior_low is not None and price < prior_low

    return {
        "price": price,
        "sma7": sma7,
        "sma30": sma30,
        "pos30": pos30,
        "drawdown_pct": drawdown_pct,
        "down_streak": down_streak,
        "d1_pct": d1_pct,
        "d3_pct": d3_pct,
        "inr_d1_pct": inr_d1_pct,
        "is_new_30day_low": is_new_30day_low,
        "window_size": len(window30),
    }


def evaluate(features: Features) -> Signal:
    s = config.SIGNAL
    price = features["price"]
    sma7 = features["sma7"]
    sma30 = features["sma30"]
    pos30 = features["pos30"]
    d1_pct = features["d1_pct"]

    reasons: List[str] = []
    verdict = "HOLD"

    if pos30 is not None and pos30 <= s["strong_buy_pos30_max"] and sma30 is not None and price < sma30:
        verdict = "STRONG BUY"
        reasons.append(f"price is near the 30-day low (position {pos30:.0%} of the range)")
        reasons.append(f"and below the 30-day average (₹{sma30:,.0f})")
    elif d1_pct is not None and d1_pct <= s["buy_d1_pct_max"] and sma7 is not None and price < sma7:
        verdict = "BUY"
        reasons.append(f"price fell {abs(d1_pct):.2f}% today")
        reasons.append(f"and is below the 7-day average (₹{sma7:,.0f}) — a real dip, not a bounce")
    elif sma30 is not None and price < sma30:
        verdict = "ACCUMULATE"
        reasons.append(f"price (₹{price:,.0f}) is below the 30-day average (₹{sma30:,.0f})")
    elif (pos30 is not None and pos30 >= s["wait_pos30_min"]) or (
        sma30 is not None and price > sma30 * s["wait_sma30_mult"]
    ):
        verdict = "WAIT"
        if pos30 is not None and pos30 >= s["wait_pos30_min"]:
            reasons.append(f"price is near the 30-day high (position {pos30:.0%} of the range)")
        if sma30 is not None and price > sma30 * s["wait_sma30_mult"]:
            reasons.append(f"price is {(price / sma30 - 1) * 100:.1f}% above the 30-day average")
    else:
        reasons.append("price is mid-range — no strong signal either way")

    if features["is_new_30day_low"]:
        reasons.append("today is a new 30-day low")
    if features["down_streak"] >= 3:
        reasons.append(f"{features['down_streak']} consecutive days of decline")
    if features["inr_d1_pct"] is not None and features["inr_d1_pct"] >= 0.3:
        reasons.append(f"rupee weakened {features['inr_d1_pct']:.2f}% vs USD — may keep local gold elevated")

    confidence = "full" if features["window_size"] >= s["min_history_for_full_confidence"] else "low"

    return {"verdict": verdict, "reasons": reasons, "confidence": confidence, "features": features}


def is_dip_alert(features: Features) -> bool:
    s = config.SIGNAL
    d1 = features["d1_pct"]
    d3 = features["d3_pct"]
    if d1 is not None and d1 <= s["dip_alert_d1_pct_max"]:
        return True
    if d3 is not None and d3 <= s["dip_alert_d3_pct_max"]:
        return True
    if features["is_new_30day_low"]:
        return True
    return False


def true_cost_22k_10g(rate_22k: float, making_charge_pct: Optional[float] = None) -> float:
    """What 10g of 22K jewellery actually costs: metal + making charges + GST."""
    mc = config.DEFAULT_MAKING_CHARGE_PCT if making_charge_pct is None else making_charge_pct
    subtotal = rate_22k * 10 * (1 + mc)
    return round(subtotal * (1 + config.GST_PCT), 2)
