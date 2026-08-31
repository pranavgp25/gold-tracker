"""
Persistence layer. history.json is the whole database: an append-only,
date-deduped list of reconciled daily records, sorted ascending. latest.json
is a denormalised snapshot (latest record + verdict + alert bookkeeping) that
the static dashboard reads directly without needing to walk the full history.

The workflow runs twice a day, so upsert_record() updates today's entry in
place on the second run rather than appending a duplicate.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from src import config


def load_history() -> List[Dict[str, Any]]:
    if not config.HISTORY_PATH.exists():
        return []
    with open(config.HISTORY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("records", [])


def save_history(records: List[Dict[str, Any]]) -> None:
    deduped: Dict[str, Dict[str, Any]] = {}
    for r in records:
        deduped[r["date"]] = r  # later entries in the input list win
    ordered = [deduped[d] for d in sorted(deduped.keys())]
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump({"records": ordered}, f, indent=2, ensure_ascii=False)
        f.write("\n")


def upsert_record(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Insert `record`, replacing any existing entry for the same date."""
    history = load_history()
    history.append(record)
    save_history(history)
    return load_history()


def load_latest() -> Dict[str, Any]:
    if not config.LATEST_PATH.exists():
        return {}
    with open(config.LATEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_latest(snapshot: Dict[str, Any]) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.LATEST_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
        f.write("\n")
