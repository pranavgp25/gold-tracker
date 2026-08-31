import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import signal


def _series(prices, usd_inr=None):
    hist = []
    for i, p in enumerate(prices):
        rec = {"date": f"2026-01-{i+1:02d}", "k24": p}
        if usd_inr:
            rec["usd_inr"] = usd_inr[i]
        hist.append(rec)
    return hist


def test_monotonic_decline_to_30day_low_is_strong_buy():
    # 35 days, steadily declining -> today is the 30-day low and below sma30
    prices = [100 - i * 0.5 for i in range(35)]  # 100.0 down to 83.0
    hist = _series(prices)
    feats = signal.compute_features(hist)
    result = signal.evaluate(feats)
    assert result["verdict"] == "STRONG BUY", result
    assert feats["is_new_window_low"] is True
    assert result["confidence"] == "full"


def test_rally_to_30day_high_is_wait():
    prices = [100 + i * 0.5 for i in range(35)]  # steadily rising
    hist = _series(prices)
    feats = signal.compute_features(hist)
    result = signal.evaluate(feats)
    assert result["verdict"] == "WAIT", result


def test_short_history_does_not_raise_and_flags_low_confidence():
    prices = [100, 99, 101, 98, 97]  # only 5 days
    hist = _series(prices)
    feats = signal.compute_features(hist)
    result = signal.evaluate(feats)
    assert result["confidence"] == "low"
    assert result["verdict"] in {"STRONG BUY", "BUY", "ACCUMULATE", "WAIT", "HOLD"}


def test_short_window_never_claims_30day_in_reasons_text():
    # Regression test: with only 7 days of real history, a new low must be
    # described as a "7-day low", never a "30-day low" — a shorter window
    # cannot honestly claim to have checked 30 days of prices.
    prices = [110, 108, 106, 104, 102, 101, 100]  # 7 days, monotonic decline
    hist = _series(prices)
    feats = signal.compute_features(hist)
    assert feats["window_size"] == 7
    result = signal.evaluate(feats)
    reasons_text = " ".join(result["reasons"])
    assert "30-day" not in reasons_text
    assert "7-day" in reasons_text


def test_single_day_history_does_not_raise():
    hist = _series([100])
    feats = signal.compute_features(hist)
    result = signal.evaluate(feats)
    assert result["features"]["d1_pct"] is None
    assert result["verdict"] in {"STRONG BUY", "BUY", "ACCUMULATE", "WAIT", "HOLD"}


def test_dip_alert_fires_on_big_single_day_drop():
    prices = [100] * 29 + [100, 98.5]  # last day drops 1.5%
    hist = _series(prices)
    feats = signal.compute_features(hist)
    assert signal.is_dip_alert(feats) is True


def test_dip_alert_silent_on_flat_market():
    prices = [100] * 32
    hist = _series(prices)
    feats = signal.compute_features(hist)
    assert signal.is_dip_alert(feats) is False


def test_new_30day_low_flag():
    prices = list(range(130, 100, -1))  # 30 strictly decreasing values
    hist = _series(prices)
    feats = signal.compute_features(hist)
    assert feats["is_new_window_low"] is True


def test_true_cost_includes_making_charge_and_gst():
    # 22K rate ₹14,385: 10g -> 143850 * 1.10 * 1.03
    cost = signal.true_cost_22k_10g(14385, making_charge_pct=0.10)
    expected = round(14385 * 10 * 1.10 * 1.03, 2)
    assert cost == expected


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests)-failed}/{len(tests)} passed")
    return failed == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
