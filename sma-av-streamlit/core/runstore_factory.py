# core/runstore_factory.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.runs_store import RunStore


def make_runstore() -> RunStore:
    """Create RunStore pointing to the same DB everywhere."""
    db_path = Path(__file__).resolve().parents[1] / "avops.db"
    try:
        return RunStore(db_path=db_path)  # newer signature
    except TypeError:
        return RunStore()  # older signature (no-arg)


def _call_first(obj: Any, candidates: list[str], *args, **kwargs):
    """Call the first method that exists on obj; no-op if none exist."""
    for name in candidates:
        fn = getattr(obj, name, None)
        if callable(fn):
            return fn(*args, **kwargs)
    return None


def record_run_start(
    store: RunStore,
    *,
    run_id: str,
    name: str,
    agent_id: Any,
    recipe_id: Any,
    trigger: str,
    started_at: Optional[datetime] = None,
) -> None:
    started_at = started_at or datetime.now(timezone.utc)
    row: Dict[str, Any] = {
        "id": run_id,
        "name": name,
        "agent_id": agent_id,
        "recipe_id": recipe_id,
        "trigger": trigger,
        "started_at": started_at.isoformat(),
        "status": "running",
        "ok": None,
    }
    _call_first(store, ["append", "add", "insert", "write", "put", "upsert"], row)


def record_run_finish(
    store: RunStore,
    *,
    run_id: str,
    status: str,                       # "success" | "failed"
    error: Optional[str],
    started_at: Optional[datetime],
    finished_at: Optional[datetime] = None,
    duration_ms: Optional[float] = None,
) -> None:
    finished_at = finished_at or datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "id": run_id,
        "finished_at": finished_at.isoformat(),
        "status": status,
        "ok": (status == "success"),
    }
    if duration_ms is None and started_at:
        duration_ms = (finished_at - started_at).total_seconds() * 1000.0
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    if error:
        payload["error"] = error

    # Prefer update; fall back to a write/upsert variant
    _call_first(store, ["update", "upsert", "append", "write", "put"], payload)
