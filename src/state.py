"""Persisted state: which notice ids we've already processed.

Stored as {"seen": {id: modifiedDate}, "last_run": iso_timestamp, "bootstrapped": bool}
so we can prune entries older than SEEN_ID_MAX_AGE_DAYS instead of growing forever.
"""
import json
import os
from datetime import datetime, timedelta, timezone

from . import config


def load():
    if not os.path.exists(config.STATE_PATH):
        return {"seen": {}, "last_run": None, "bootstrapped": False}
    with open(config.STATE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("seen", {})
    data.setdefault("last_run", None)
    data.setdefault("bootstrapped", False)
    return data


def save(state, run_timestamp):
    state["last_run"] = run_timestamp
    _prune(state)
    os.makedirs(os.path.dirname(config.STATE_PATH) or ".", exist_ok=True)
    with open(config.STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)


def mark_seen(state, notice_id, modified_date):
    state["seen"][notice_id] = modified_date


def is_seen(state, notice_id):
    return notice_id in state["seen"]


def _prune(state):
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.SEEN_ID_MAX_AGE_DAYS)
    kept = {}
    for notice_id, modified_date in state["seen"].items():
        try:
            ts = datetime.fromisoformat(modified_date.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            kept[notice_id] = modified_date
            continue
        if ts >= cutoff:
            kept[notice_id] = modified_date
    state["seen"] = kept
