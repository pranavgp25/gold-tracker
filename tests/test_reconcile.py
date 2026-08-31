import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import reconcile


def test_median_headline_unaffected_by_outlier():
    primary = {"source": "goodreturns", "date": "2026-08-31", "k24": 15692.0, "k22": 14385.0, "k18": 11800.0}
    cross_checks = [
        {"source": "policybazaar", "date": "2026-08-31", "k24": 15335.0, "k22": 14605.0},
        {"source": "fivepaisa", "date": "2026-08-31", "k24": 47000.0, "k22": 14520.0},  # 3x outlier
    ]
    rec = reconcile.reconcile(primary, cross_checks, spot_24k=13613.30, usd_inr=95.39)

    assert rec["k24"] == 15692.0, "headline must be goodreturns' own value, not a blended one"
    assert "fivepaisa" in rec["outlier_sources"]
    assert "policybazaar" not in rec["outlier_sources"]
    assert rec["cross_check_median_24"] == 15335.0  # outlier excluded from the cross-check median
    assert rec["stale"] is False


def test_india_premium_computed_against_spot():
    primary = {"source": "goodreturns", "date": "2026-08-31", "k24": 15692.0, "k22": 14385.0}
    rec = reconcile.reconcile(primary, [], spot_24k=13613.30, usd_inr=95.39)
    assert abs(rec["india_premium"] - (15692.0 / 13613.30)) < 1e-3  # india_premium is rounded to 4dp


def test_missing_cross_checks_does_not_raise():
    primary = {"source": "goodreturns", "date": "2026-08-31", "k24": 15692.0, "k22": 14385.0}
    rec = reconcile.reconcile(primary, [], spot_24k=None, usd_inr=None)
    assert rec["cross_check_median_24"] is None
    assert rec["india_premium"] is None
    assert rec["spread_pct"] is None


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
