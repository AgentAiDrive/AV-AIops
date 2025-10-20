"""
pages/Run_Detail.py
--------------------

Dedicated page for viewing the full details of a workflow run.  This page is
linked from the Dashboard and accepts a ``run_id`` query parameter.  It
retrieves the run information via the shared run store and presents all
step events and artifacts without pagination.  If no run ID is provided or
the run is not found, informative messages are shown instead of crashing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import streamlit as st

from core.runstore_factory import make_runstore

st.set_page_config(page_title="Run Details", page_icon="🔎", layout="wide")
st.title("🔎 Run Details")

# Extract run_id from query parameters
params = st.experimental_get_query_params()
run_id_vals = params.get("run_id") or []
try:
    run_id = int(run_id_vals[0]) if run_id_vals else None
except (TypeError, ValueError):
    run_id = run_id_vals[0] if run_id_vals else None

if run_id is None:
    st.info("No run_id provided in the URL.")
    st.stop()

# Instantiate run store and fetch details
store = make_runstore()
try:
    detail = store.run_details(run_id)  # type: ignore[attr-defined]
except Exception:
    detail = {}

if not detail:
    st.warning(f"Run with ID {run_id} not found.")
    st.stop()

# Header
st.header(f"Run #{run_id}: {detail.get('name') or 'Run'}")
st.caption(
    f"Status: {detail.get('status','—')} · "
    f"Duration: {int(detail.get('duration_ms') or 0)} ms · "
    f"Started: {detail.get('started_at')} · Finished: {detail.get('finished_at')}"
)

left, right = st.columns([2, 1], vertical_alignment="top")

with left:
    st.markdown("**Steps**")
    steps: List[Dict[str, Any]] = detail.get("steps", [])  # type: ignore[assignment]
    if not steps:
        st.caption("No step events recorded.")
    else:
        for s in steps:
            phase = s.get("phase") or "—"
            msg = s.get("message") or s.get("msg") or "—"
            stts = s.get("status") or "—"
            ts = s.get("ts") or s.get("time") or "—"
            with st.expander(f"[{phase}] {msg}  —  {stts} · {ts}", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Payload**")
                    st.json(s.get("payload") or {})
                with c2:
                    st.markdown("**Result**")
                    st.json(s.get("result") or {})

with right:
    st.markdown("**Artifacts**")
    arts: List[Dict[str, Any]] = detail.get("artifacts", [])  # type: ignore[assignment]
    if not arts:
        st.caption("No artifacts captured.")
        st.write("—")
    else:
        for a in arts:
            with st.container(border=True):
                st.write(f"**{a.get('kind','artifact')}** — {a.get('title','')}")
                if a.get("url"):
                    st.write(a["url"])
                if a.get("external_id"):
                    st.caption(f"id: {a['external_id']}")
                if a.get("data"):
                    st.json(a["data"])
