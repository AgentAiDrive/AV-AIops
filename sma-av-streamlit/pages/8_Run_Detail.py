"""Dedicated run detail view with pagination for steps and artifacts."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import streamlit as st

from core.runs_store import RunStore


def _make_store() -> RunStore:
    db_path = Path(__file__).resolve().parents[1] / "avops.db"
    try:
        return RunStore(db_path=db_path)
    except TypeError:
        return RunStore()


def _to_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _get_params() -> Dict[str, Any]:
    if hasattr(st, "query_params"):
        return dict(st.query_params)
    return st.experimental_get_query_params()  # type: ignore[attr-defined]


def _ensure_int(value: Any) -> Any:
    try:
        return int(value)
    except Exception:
        return value


st.set_page_config(page_title="Run Detail", layout="wide")
st.title("🔎 Workflow Run Detail")

params = _get_params()
run_id_raw = params.get("run_id")
if isinstance(run_id_raw, list):
    run_id_raw = run_id_raw[0] if run_id_raw else None

if run_id_raw is None:
    st.error("Append `?run_id=<id>` to the URL (or use the dashboard link) to view a run.")
    st.stop()

run_id = _ensure_int(run_id_raw)
store = _make_store()

detail = store.run_details(run_id)
if not detail:
    st.error(f"Run {run_id} was not found in RunStore.")
    st.stop()

st.page_link("pages/8_Dashboard.py", label="⬅ Back to dashboard", icon="⬅")

started_at = _to_dt(detail.get("started_at"))
finished_at = _to_dt(detail.get("finished_at"))

col1, col2, col3 = st.columns(3)
col1.metric("Status", detail.get("status", "unknown"))
col2.metric("Duration (ms)", f"{(detail.get('duration_ms') or 0):.0f}")
error_msg = detail.get("error") or "—"
col3.metric("Error", error_msg if len(error_msg) < 32 else error_msg[:29] + "…")

st.caption(
    f"Started: {started_at or '—'} · Finished: {finished_at or '—'} · Trigger: {detail.get('trigger', 'manual')}"
)

meta = detail.get("meta") or {}
with st.expander("Metadata", expanded=False):
    st.json(meta)

steps = detail.get("steps", [])
st.subheader(f"Steps ({len(steps)})")
if not steps:
    st.info("No step events captured for this run.")
else:
    step_page_size = 8
    step_pages = max(1, math.ceil(len(steps) / step_page_size))
    step_page = int(
        st.number_input(
            "Step page",
            min_value=1,
            max_value=step_pages,
            value=1,
            step=1,
            key="run_detail_step_page",
        )
    )
    start = (step_page - 1) * step_page_size
    end = min(start + step_page_size, len(steps))
    st.caption(f"Showing steps {start + 1}-{end} of {len(steps)}.")
    for s in steps[start:end]:
        ts = s.get("ts") or s.get("time") or "—"
        phase = s.get("phase") or "—"
        header = f"[{phase}] {s.get('message') or s.get('msg') or '—'}"
        with st.expander(f"{header} · {ts}"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Payload**")
                st.json(s.get("payload") or {})
            with c2:
                st.markdown("**Result**")
                st.json(s.get("result") or {})

arts = detail.get("artifacts", [])
st.subheader(f"Artifacts ({len(arts)})")
if not arts:
    st.info("No artifacts stored for this run.")
else:
    art_page_size = 6
    art_pages = max(1, math.ceil(len(arts) / art_page_size))
    art_page = int(
        st.number_input(
            "Artifact page",
            min_value=1,
            max_value=art_pages,
            value=1,
            step=1,
            key="run_detail_art_page",
        )
    )
    start = (art_page - 1) * art_page_size
    end = min(start + art_page_size, len(arts))
    st.caption(f"Showing artifacts {start + 1}-{end} of {len(arts)}.")
    for a in arts[start:end]:
        with st.container(border=True):
            st.write(f"**{a.get('kind', 'artifact')}** — {a.get('title', '')}")
            if a.get("url"):
                st.write(a["url"])
            if a.get("external_id"):
                st.caption(f"id: {a['external_id']}")
            if a.get("data"):
                st.json(a["data"])
