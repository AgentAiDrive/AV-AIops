"""
pages/8_Dashboard.py
---------------------

An enhanced dashboard for AV AI Ops that provides a live view of workflow
runs along with interactive controls for filtering, pagination, step/artefact
exploration and a quick summary of current workflows.  The page makes
minimal assumptions about the underlying run log store by delegating to a
factory (`make_runstore`) that returns a compatible interface.  It falls
back gracefully when optional dependencies (e.g. streamlit_autorefresh)
aren't installed.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from core.runstore_factory import make_runstore
from core.db.session import get_session
from core.workflow.service import list_workflows, compute_status


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard")
st.caption("AV AI OPS — Live view of workflow runs, steps, artifacts, and KPIs.")
# ---------------------------------------------------------------------------
# Instantiate the run store via factory
# ---------------------------------------------------------------------------
store = make_runstore()


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Filters")
    win = st.selectbox("Time window", ["24h", "7d", "30d", "All"], index=0)
    statuses = st.multiselect("Status", ["running", "success", "failed"], default=["running", "success", "failed"])
    page_size = st.slider("Runs per page", min_value=5, max_value=50, value=10, step=5)
    auto = st.toggle("Auto-refresh (5s)", value=False)
    st.caption("Tip: If nothing appears, run a Workflow or /sop from Chat.")

if auto:
    # Attempt to use streamlit_autorefresh if installed
    try:
        from streamlit_autorefresh import st_autorefresh

        st_autorefresh(interval=5000, key="dash_refresh")
    except Exception:
        st.info("Install `streamlit-autorefresh` for auto refresh, or click refresh.")


# ---------------------------------------------------------------------------
# Time window → since
# ---------------------------------------------------------------------------
now = datetime.now(timezone.utc)
since: Optional[datetime] = None
if win == "24h":
    since = now - timedelta(hours=24)
elif win == "7d":
    since = now - timedelta(days=7)
elif win == "30d":
    since = now - timedelta(days=30)


# ---------------------------------------------------------------------------
# Helpers for heterogeneous stores
# ---------------------------------------------------------------------------
def _to_dt(value: Any) -> Optional[datetime]:
    """Parse various date representations into a tz-aware UTC datetime."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _stats_compat(store, *, hours: Optional[int] = None, since: Optional[datetime] = None) -> Dict[str, Any]:
    """Call store.stats with an available signature."""
    if hours is not None:
        try:
            return store.stats(hours=hours)
        except TypeError:
            pass
    if since is not None:
        try:
            return store.stats(since=since)
        except TypeError:
            pass
    return store.stats()


def _latest_runs_compat(store, *, limit: int, statuses: List[str], since: Optional[datetime]) -> List[Dict[str, Any]]:
    """Fetch runs from the store using whatever API it supports."""
    # Try the current RunStore API first
    try:
        rows = store.latest_runs(limit=limit, status=statuses)
    except Exception:
        # Fallback to alternative methods for other store implementations
        try:
            hours = None
            if since:
                hours = max(1, int((datetime.now(timezone.utc) - since).total_seconds() // 3600))
            rows = store.recent(limit=limit, hours=hours or 24)
        except Exception:
            try:
                rows = store.list_runs()
            except Exception:
                rows = []

    out: List[Dict[str, Any]] = []
    for r in rows:
        if isinstance(r, str):
            try:
                r = json.loads(r)
            except Exception:
                continue
        out.append(r)

    # Filter by time window using tz-aware comparisons
    if since:
        filtered = []
        for r in out:
            ts = _to_dt(
                r.get("started_at")
                or r.get("start")
                or r.get("created_at")
                or r.get("ts")
                or r.get("time")
            ) or datetime.min.replace(tzinfo=timezone.utc)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= since:
                filtered.append(r)
        out = filtered

    # Filter by status if the store didn't handle it
    def _status_of(rr: Dict[str, Any]) -> str:
        if rr.get("status"):
            return str(rr["status"])
        if rr.get("running"):
            return "running"
        if rr.get("ok") is True:
            return "success"
        if rr.get("ok") is False:
            return "failed"
        return "unknown"

    out = [r for r in out if _status_of(r) in statuses]
    return out


def _normalize_run(r: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a run dict into a common shape for display."""
    meta = r.get("meta") or {}
    started = _to_dt(
        r.get("started_at")
        or r.get("start")
        or r.get("created_at")
        or r.get("ts")
        or r.get("time")
    )
    finished = _to_dt(
        r.get("finished_at")
        or r.get("end")
        or r.get("completed_at")
        or r.get("finish")
        or r.get("done_at")
    )
    duration_ms = r.get("duration_ms")
    if duration_ms is None:
        if r.get("duration_s") is not None:
            try:
                duration_ms = float(r["duration_s"]) * 1000.0
            except Exception:
                duration_ms = None
        elif started and finished:
            duration_ms = (finished - started).total_seconds() * 1000.0

    status = r.get("status")
    if not status:
        if r.get("running"):
            status = "running"
        elif r.get("ok") is True:
            status = "success"
        elif r.get("ok") is False:
            status = "failed"
        else:
            status = "unknown"

    name = r.get("name") or r.get("title") or meta.get("workflow_name") or "Run"
    agent_id = r.get("agent_id") or meta.get("agent_id")
    recipe_id = r.get("recipe_id") or meta.get("recipe_id")
    trigger = r.get("trigger") or meta.get("trigger")
    return {
        "id": r.get("id") or r.get("run_id") or r.get("trace_id") or "",
        "name": name,
        "status": status,
        "trigger": trigger,
        "agent_id": agent_id,
        "recipe_id": recipe_id,
        "duration_ms": duration_ms or 0.0,
        "started_at": started,
        "finished_at": finished,
        "error": r.get("error"),
        "raw": r,
    }


def _run_details_compat(store, run_id: Any) -> Dict[str, Any]:
    """Fetch detailed run data from the store, with fallback."""
    try:
        return store.run_details(run_id)
    except Exception:
        return {"id": run_id, "steps": [], "artifacts": []}


# ---------------------------------------------------------------------------
# KPI section
# ---------------------------------------------------------------------------
hours_for_stats = None
if since:
    hours_for_stats = max(1, int((datetime.now(timezone.utc) - since).total_seconds() // 3600))

stats = _stats_compat(store, hours=hours_for_stats, since=since)
runs_total = stats.get("runs") or stats.get("count") or 0
success_rate = stats.get("success_rate")
if success_rate is None:
    ok = stats.get("ok") or 0
    success_rate = (100.0 * float(ok) / float(runs_total)) if runs_total else 0.0
p95_ms = stats.get("p95_ms")
if p95_ms is None:
    p95_s = stats.get("p95_s")
    p95_ms = (float(p95_s) * 1000.0) if p95_s is not None else 0.0
last_error = stats.get("last_error") or ""

c1, c2, c3, c4 = st.columns(4)
c1.metric("Runs", f"{runs_total}")
c2.metric("Success rate", f"{success_rate:.1f}%")
c3.metric("p95 duration", f"{p95_ms:.0f} ms")
c4.metric("Last error", last_error or "—")


# ---------------------------------------------------------------------------
# Recent runs table with pagination
# ---------------------------------------------------------------------------
rows_raw = _latest_runs_compat(store, limit=200, statuses=statuses, since=since)
rows = [_normalize_run(r) for r in rows_raw]

# Drop runs with no timestamp to avoid pandas sort errors
rows = [r for r in rows if r["started_at"] is not None]

if not rows:
    st.info("No runs in this window. Trigger a workflow from **🧩 Workflows** or use **/sop** in **💬 Chat**.")
    st.stop()

records = [
    {
        "id": r["id"],
        "name": r["name"],
        "status": r["status"],
        "trigger": r["trigger"],
        "agent_id": r["agent_id"],
        "recipe_id": r["recipe_id"],
        "duration (ms)": round(float(r["duration_ms"] or 0.0), 2),
        "started_at": r["started_at"],
    }
    for r in rows
]
df_all = pd.DataFrame(records)
df_all.sort_values("started_at", ascending=False, inplace=True)

total_runs = len(df_all)
page_size = max(1, int(page_size))
total_pages = max(1, math.ceil(total_runs / page_size))
if "runs_page" not in st.session_state:
    st.session_state["runs_page"] = 1
if st.session_state["runs_page"] > total_pages:
    st.session_state["runs_page"] = total_pages

page = int(
    st.number_input(
        "Page",
        min_value=1,
        max_value=total_pages,
        value=st.session_state["runs_page"],
        step=1,
        key="runs_page_widget",
    )
)
st.session_state["runs_page"] = page

start_idx = (page - 1) * page_size
end_idx = min(start_idx + page_size, total_runs)
df_page = df_all.iloc[start_idx:end_idx].copy()
df_page["Details"] = df_page["id"].apply(lambda rid: f"/Run_Detail?run_id={rid}")

st.subheader("Recent Runs")
st.caption(f"Showing runs {start_idx + 1}-{end_idx} of {total_runs}.")
st.data_editor(
    df_page,
    use_container_width=True,
    hide_index=True,
    disabled=True,
    column_config={
        "Details": st.column_config.LinkColumn("Details", display_text="Open"),
    },
)


# ---------------------------------------------------------------------------
# Trend chart
# ---------------------------------------------------------------------------
st.subheader("Run Trend")
trend = (
    df_all.groupby(df_all["started_at"].dt.floor("H"))["id"]
    .count()
    .reset_index()
    .rename(columns={"id": "runs"})
)
st.line_chart(trend.set_index("started_at"))


# ---------------------------------------------------------------------------
# Run details explorer
# ---------------------------------------------------------------------------
st.subheader("Run Details")
selected_id = st.selectbox("Select a run ID", options=df_all["id"].tolist(), index=0)
try:
    selected_id_int = int(selected_id)
except (TypeError, ValueError):
    selected_id_int = selected_id

# Reset pagination for new selection
if st.session_state.get("current_detail_id") != selected_id_int:
    st.session_state["current_detail_id"] = selected_id_int
    st.session_state[f"steps_page_{selected_id_int}"] = 1
    st.session_state[f"artifacts_page_{selected_id_int}"] = 1

detail = _run_details_compat(store, selected_id_int)

left, right = st.columns([2, 1], vertical_alignment="top")

with left:
    selected_row = next((r for r in rows if r["id"] == selected_id_int), None)
    title = (selected_row or {}).get("name") or detail.get("name") or "Run"
    agent_id = (selected_row or {}).get("agent_id") or detail.get("agent_id")
    recipe_id = (selected_row or {}).get("recipe_id") or detail.get("recipe_id")
    status = (selected_row or {}).get("status") or detail.get("status")
    duration_ms = (selected_row or {}).get("duration_ms") or detail.get("duration_ms") or 0

    st.markdown(f"""**{title}** &nbsp;•&nbsp; #{selected_id_int}""")
    st.caption(
        f"Agent={agent_id} · Recipe={recipe_id} · Status={status} · Duration={int(duration_ms)} ms"
    )

    detail_url = f"/Run_Detail?run_id={selected_id_int}"
    st.link_button("🔎 Open full run details", detail_url, type="secondary")

    # Steps
    st.markdown("**Steps**")
    steps = detail.get("steps", [])
    if not steps:
        st.caption("No step events recorded yet.")
    else:
        step_page_size = 5
        step_total = len(steps)
        step_pages = max(1, math.ceil(step_total / step_page_size))
        step_state_key = f"steps_page_{selected_id_int}"
        current_step_page = min(st.session_state.get(step_state_key, 1), step_pages)
        current_step_page = int(
            st.number_input(
                "Step page",
                min_value=1,
                max_value=step_pages,
                value=current_step_page,
                step=1,
                key=f"{step_state_key}_widget",
            )
        )
        st.session_state[step_state_key] = current_step_page
        step_start = (current_step_page - 1) * step_page_size
        step_end = min(step_start + step_page_size, step_total)
        st.caption(f"Showing steps {step_start + 1}-{step_end} of {step_total}.")
        for s in steps[step_start:step_end]:
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
    arts = detail.get("artifacts", [])
    if not arts:
        st.caption("No artifacts captured.")
        st.write("—")
    else:
        art_page_size = 4
        art_total = len(arts)
        art_pages = max(1, math.ceil(art_total / art_page_size))
        art_state_key = f"artifacts_page_{selected_id_int}"
        current_art_page = min(st.session_state.get(art_state_key, 1), art_pages)
        current_art_page = int(
            st.number_input(
                "Artifact page",
                min_value=1,
                max_value=art_pages,
                value=current_art_page,
                step=1,
                key=f"{art_state_key}_widget",
            )
        )
        st.session_state[art_state_key] = current_art_page
        art_start = (current_art_page - 1) * art_page_size
        art_end = min(art_start + art_page_size, art_total)
        st.caption(f"Showing artifacts {art_start + 1}-{art_end} of {art_total}.")
        for a in arts[art_start:art_end]:
            with st.container(border=True):
                st.write(f"**{a.get('kind','artifact')}** — {a.get('title','')}")
                if a.get("url"):
                    st.write(a["url"])
                if a.get("external_id"):
                    st.caption(f"id: {a['external_id']}")
                if a.get("data"):
                    st.json(a["data"])


# ---------------------------------------------------------------------------
# Workflows panel (for reference)
# ---------------------------------------------------------------------------
st.subheader("Workflows")
with get_session() as db:
    wfs = list_workflows(db)
    if not wfs:
        st.info("No workflows defined yet.")
    for wf in wfs:
        status = compute_status(wf)
        dot = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(status, "⚪")
        st.markdown(
            f"{dot} **{wf.name}** · Agent `{wf.agent_id}` · Recipe `{wf.recipe_id}`"
            f"<br/>Last: {wf.last_run_at or '—'} · Next: {wf.next_run_at or '—'}",
            unsafe_allow_html=True,
        )

