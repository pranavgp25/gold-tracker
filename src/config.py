"""
Central configuration: thresholds, karats, source list, cron/timezone constants.
Keep tunable numbers here rather than inline in logic modules.
"""
from __future__ import annotations

# --- Karats we track --------------------------------------------------------
KARATS = ["24k", "22k", "18k"]

# --- Signal engine thresholds ------------------------------------------------
# See src/signal.py for how these combine into a verdict.
SIGNAL = {
    "strong_buy_pos30_max": 0.15,      # near the 30-day floor
    "buy_d1_pct_max": -0.8,            # a single-day drop of >= 0.8% ...
    "wait_pos30_min": 0.85,            # near the 30-day ceiling
    "wait_sma30_mult": 1.03,           # ... or > 3% above the 30-day average
    "dip_alert_d1_pct_max": -0.8,
    "dip_alert_d3_pct_max": -1.5,
    "min_history_for_full_confidence": 30,
}

# --- Jewellery true-cost estimate --------------------------------------------
DEFAULT_MAKING_CHARGE_PCT = 0.10   # 10%, editable on the dashboard
GST_PCT = 0.03                     # 3% GST on gold jewellery in India

# --- Reconciliation -----------------------------------------------------------
OUTLIER_REJECT_PCT = 0.05   # reject a source that moved > 5% vs its own last value

# --- HTTP ----------------------------------------------------------------------
HTTP_TIMEOUT_SECONDS = 20
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# --- Paths -----------------------------------------------------------------
import pathlib
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
# Lives under docs/ (not repo-root) because GitHub Pages only serves the
# configured /docs folder — this lets the same file be both the workflow's
# write target and the dashboard's fetch target, with no separate publish step.
DATA_DIR = REPO_ROOT / "docs" / "data"
HISTORY_PATH = DATA_DIR / "history.json"
LATEST_PATH = DATA_DIR / "latest.json"

# --- Local dev credentials (per user's global security rules) ----------------
LOCAL_ENV_PATH = r"C:\credentials\.env"
