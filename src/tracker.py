"""
Orchestrator / CLI entrypoint. Run twice a day by .github/workflows/track.yml:

  python -m src.tracker --digest      # morning run: full digest + dip check
  python -m src.tracker                # evening run: dip check only, silent otherwise
  python -m src.tracker --dry-run --digest   # print messages, send nothing

On a cold start (empty history.json) it seeds the last 10 days from
goodreturns' own "Last 10 Days" table before doing anything else, so the
signal engine has real data to work with on day one.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from typing import List

from src import config, reconcile, signal, store
from src.notifiers.base import Notifier
from src.notifiers.telegram import TelegramNotifier
from src.sources.goodreturns import GoodReturnsSource
from src.sources.policybazaar import PolicyBazaarSource
from src.sources.fivepaisa import FivePaisaSource
from src.sources import spot as spot_module
from src.sources import fx as fx_module


def build_notifiers() -> List[Notifier]:
    # Add WhatsAppNotifier() here once src/notifiers/whatsapp.py is implemented —
    # no other change needed, tracker.py iterates this list generically.
    return [TelegramNotifier()]


def merge_gap_fill(history: List[dict], gap_rows: List[dict], source_label: str) -> List[dict]:
    """Add `gap_rows` for any date not already present in `history`. Never
    overwrites an existing date — used to patch holes in goodreturns' sparser
    backfill table with 5paisa's denser one, without ever treating a
    secondary source as more authoritative than the primary for a date both
    cover. See fivepaisa.py's docstring for why that boundary matters."""
    existing_dates = {r["date"] for r in history}
    added = [
        {
            "date": row["date"],
            "k24": row["k24"],
            "k22": row["k22"],
            "k18": None,
            "primary_source": source_label,
            "cross_check_median_24": None,
            "spread_pct": None,
            "outlier_sources": [],
            "india_premium": None,
            "usd_inr": None,
            "stale": False,
            "backfilled": True,
        }
        for row in gap_rows
        if row["date"] not in existing_dates
    ]
    if added:
        print(f"[tracker] gap-filled {len(added)} day(s) from {source_label}: "
              f"{[r['date'] for r in added]}")
    return history + added


def seed_history_if_needed(dry_run: bool = False) -> None:
    history = store.load_history()
    if len(history) >= 2:
        return
    if dry_run:
        print("[tracker] history has < 2 records but --dry-run set — skipping seed write")
        return
    print("[tracker] history has < 2 records — seeding from goodreturns' 10-day table")
    rows = GoodReturnsSource().backfill_10day()
    if not rows:
        print("[tracker] backfill unavailable — starting from today only")
        return
    seeded = merge_gap_fill([], rows, "goodreturns")
    # goodreturns' table skips some calendar days; 5paisa's own 10-day table is
    # denser, so use it only to fill those gaps, never to override a date
    # goodreturns already answered.
    seeded = merge_gap_fill(seeded, FivePaisaSource().backfill_10day(), "fivepaisa (gap-fill)")
    store.save_history(seeded)
    print(f"[tracker] seeded {len(seeded)} days of history")


def fetch_and_reconcile():
    primary = GoodReturnsSource().fetch()
    spot_rec = spot_module.fetch_spot()
    usd_inr = fx_module.fetch_usd_inr()

    if primary is None:
        print("[tracker] PRIMARY SOURCE FAILED — carrying forward last known record as stale")
        history = store.load_history()
        if not history:
            print("[tracker] no prior history to carry forward — nothing to do")
            return None
        stale = dict(history[-1])
        stale["date"] = date.today().isoformat()
        stale["stale"] = True
        return stale

    cross_checks = []
    for cls in (PolicyBazaarSource, FivePaisaSource):
        rec = cls().fetch()
        if rec is not None:
            cross_checks.append(rec)

    spot_24k = spot_rec["spot_24k"] if spot_rec else None
    reconciled = reconcile.reconcile(primary, cross_checks, spot_24k, usd_inr)
    return dict(reconciled)


def build_digest_message(record: dict, sig: signal.Signal) -> str:
    price22 = record.get("k22")
    price24 = record.get("k24")
    price18 = record.get("k18")
    lines = [
        f"<b>Delhi Gold — {record['date']}</b>",
        "",
        f"24K: ₹{price24:,.0f}/g" if price24 else "24K: n/a",
        f"22K: ₹{price22:,.0f}/g" if price22 else "22K: n/a",
        f"18K: ₹{price18:,.0f}/g" if price18 else "18K: n/a (source omitted it today)",
    ]
    d1 = sig["features"]["d1_pct"]
    if d1 is not None:
        arrow = "▼" if d1 < 0 else ("▲" if d1 > 0 else "→")
        lines.append(f"Change: {arrow} {d1:+.2f}% vs yesterday")

    lines += ["", f"<b>Signal: {sig['verdict']}</b>"]
    for r in sig["reasons"]:
        lines.append(f"• {r}")

    if price22:
        cost = signal.true_cost_22k_10g(price22)
        lines += ["", f"Est. cost, 10g 22K jewellery (10% making + 3% GST): ₹{cost:,.0f}"]

    if record.get("stale"):
        lines += ["", "⚠️ Could not refresh today's rate — showing the last known price."]

    return "\n".join(lines)


def build_dip_alert_message(record: dict, sig: signal.Signal) -> str:
    price24 = record.get("k24")
    d1 = sig["features"]["d1_pct"]
    lines = [f"🔔 <b>Gold dip alert — Delhi</b>", f"24K just moved to ₹{price24:,.0f}/g"]
    if d1 is not None:
        lines.append(f"({d1:+.2f}% today)")
    lines.append(f"Signal: {sig['verdict']}")
    for r in sig["reasons"]:
        lines.append(f"• {r}")
    return "\n".join(lines)


def run(dry_run: bool, send_digest: bool) -> int:
    seed_history_if_needed(dry_run=dry_run)

    record = fetch_and_reconcile()
    if record is None:
        print("[tracker] nothing to report this run")
        return 1

    if dry_run:
        # Preview what history would look like without writing anything.
        history = [r for r in store.load_history() if r["date"] != record["date"]] + [record]
        history.sort(key=lambda r: r["date"])
    else:
        store.upsert_record(record)
        history = store.load_history()

    feats = signal.compute_features(history)
    sig = signal.evaluate(feats)

    notifiers = build_notifiers()
    latest = store.load_latest()
    today = record["date"]

    messages_sent = []

    if send_digest:
        text = build_digest_message(record, sig)
        messages_sent.append(("digest", text))

    dip = signal.is_dip_alert(feats) and not record.get("stale")
    already_alerted_today = latest.get("last_dip_alert_date") == today
    if dip and not already_alerted_today:
        text = build_dip_alert_message(record, sig)
        messages_sent.append(("dip_alert", text))

    for kind, text in messages_sent:
        print(f"--- {kind} ---\n{text}\n")
        if not dry_run:
            for notifier in notifiers:
                notifier.send(text)

    if not messages_sent:
        print("[tracker] no dip, and this is not a digest run — staying quiet")

    latest_snapshot = {
        "date": today,
        "record": record,
        "signal": sig,
        "last_dip_alert_date": today if (dip and not dry_run) else latest.get("last_dip_alert_date"),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if not dry_run:
        store.save_latest(latest_snapshot)

    return 0


def main() -> int:
    # Rupee symbol etc. can crash print() on a Windows console stuck on cp1252;
    # GitHub Actions runners are UTF-8 already, so this is a no-op there.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Delhi gold price tracker")
    parser.add_argument("--dry-run", action="store_true", help="print messages, send/save nothing")
    parser.add_argument("--digest", action="store_true", help="also send the full daily digest")
    args = parser.parse_args()
    return run(dry_run=args.dry_run, send_digest=args.digest)


if __name__ == "__main__":
    sys.exit(main())
