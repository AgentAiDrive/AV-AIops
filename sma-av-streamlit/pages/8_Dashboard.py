# sma-av-streamlit/pages/08_Dashboard.py
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

# Core stores/services
from core.runs_store import RunStore
from core.db.session import get_session
from core.workflow.service import list_workflows

st.set_page_config(page_title="Dashboard", layout="wide")
st.title("📊 Dashboard")
st.caption("AV AI OPS — Live view of workflow runs, steps, artifacts, and KPIs.")

# ---------------------------------------------------------------------------
# Store init (be liberal in how RunStore is constructed)
# ---------------------------------------------------------------------------

def _make_store() -> RunStore:
    """Instantiate RunStore with a stable DB path if supported, else fallback."""
    db_path = Path(__file__).resolve().parents[1] / "avops.db"
    try:
        # Newer RunStore that accepts a path
        return RunStore(db_path=db_path)
    except TypeError:
        # Older RunStore: no arguments
        return RunStore()

store = _make_store()

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Filters")
    win = st.selectbox("Time window", ["24h", "7d", "30d", "All"], index=0)
    statuses = st.multiselect("Status", ["running", "success", "failed"], default=["running", "success", "failed"])
    auto = st.toggle("Auto-refresh (5s)", value=False)
    st.caption("Tip: If nothing appears, run a Workflow or /sop from Chat.")

# best-effort auto refresh (only if the helper is installed)
if auto:
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=5000, key="dash_refresh")
    except Exception:
        st.info("Install `streamlit-autorefresh` for auto refresh, or click the refresh button in your browser.")

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
# Compatibility helpers (RunStore API may differ between versions)
# ---------------------------------------------------------------------------
def _stats_compat(store: RunStore, *, hours: Optional[int] = None, since: Optional[datetime] = None) -> Dict[str, Any]:
    """Call store.stats with whatever signature it supports."""
    # Prefer hours if provided
    if hours is not None:
        try:
            return store.stats(hours=hours)
        except TypeError:
            pass
    # Try since=
    if since is not None:
        try:
            return store.stats(since=since)
        except TypeError:
            pass
    # Last resort: no args
    return store.stats()

def _latest_runs_compat(store: RunStore, *, limit: int, statuses: List[str], since: Optional[datetime]) -> List[Dict[str, Any]]:
    """Fetch runs using the first available method and normalize rough filtering."""
    # Try latest_runs(limit=?, status=?)
    try:
        rows = store.latest_runs(limit=limit, status=statuses)
    except Exception:
        # Try recent(limit=?, hours=?)
        try:
            hours = None
            if since:
                hours = max(1, int((now - since).total_seconds() // 3600))
            rows = store.recent(limit=limit, hours=hours or 24)
        except Exception:
            # Try list_runs()
            try:
                rows = store.list_runs()
            except Exception:
                rows = []
    # If rows are strings (JSON), parse
    out = []
    for r in rows:
        if isinstance(r, str):
            try:
                r = json.loads(r)
            except Exception:
                continue
        out.append(r)
    # Window filter if we got ISO strings
    if since:
        iso = since.isoformat()
        out = [r for r in out if str(r.get("started_at") or r.get("start") or "") >= iso]
    # Status filter if the store didn't apply it
    def _status_of(r: Dict[str, Any]) -> str:
        if "status" in r and r["status"]:
            return str(r["status"])
        # derive from ok/running fields
        if r.get("running"):
            return "running"
        if r.get("ok") is True:
            return "success"
        if r.get("ok") is False:
            return "failed"
        return "unknown"
    out = [r for r in out if _status_of(r) in statuses]
    return out

def _to_dt(v: Any) -> Optional[datetime]:
    if not v:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:
        return None

def _normalize_run(r: Dict[str, Any]) -> Dict[str, Any]:
    """Map heterogeneous run dicts into a common shape for the UI."""
    meta = r.get("meta") or {}
    started = _to_dt(r.get("started_at") or r.get("start"))
    finished = _to_dt(r.get("finished_at") or r.get("end"))
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

def _run_details_compat(store: RunStore, run_id: Any) -> Dict[str, Any]:
    """Fetch run details if available; otherwise synthesize from recent rows."""
    try:
        return store.run_details(run_id)
    except Exception:
        # Some stores don’t expose run_details; return a minimal dict
        return {"id": run_id, "steps": [], "artifacts": []}

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
hours_for_stats = None
if since:
    hours_for_stats = max(1, int((now - since).total_seconds() // 3600))

stats = _stats_compat(store, hours=hours_for_stats, since=since)

# Normalize some expected fields with good fallbacks
runs_total = stats.get("runs") or stats.get("count") or 0
success_rate = stats.get("success_rate")
if success_rate is None:
    ok = stats.get("ok") or 0
    if runs_total:
        success_rate = 100.0 * float(ok) / float(runs_total)
    else:
        success_rate = 0.0
p95_ms = stats.get("p95_ms")
if p95_ms is None:
    # Some stores expose p95_s
    p95_s = stats.get("p95_s")
    p95_ms = (float(p95_s) * 1000.0) if p95_s is not None else 0.0
last_error = stats.get("last_error") or ""

c1, c2, c3, c4 = st.columns(4)
c1.metric("Runs", f"{runs_total}")
c2.metric("Success rate", f"{success_rate:.1f}%")
c3.metric("p95 duration", f"{p95_ms:.0f} ms")
c4.metric("Last error", last_error or "—")

# ---------------------------------------------------------------------------
# Recent runs table
# ---------------------------------------------------------------------------
rows_raw = _latest_runs_compat(store, limit=200, statuses=statuses, since=since)
rows = [_normalize_run(r) for r in rows_raw]
rows = [r for r in rows if r["started_at"] is not None]  # drop malformed

if not rows:
    st.info("No runs in this window. Trigger a workflow from **🧩 Workflows** or use **/sop** in **💬 Chat**.")
    st.stop()

df = pd.DataFrame([
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
])
df.sort_values("started_at", ascending=False, inplace=True)

st.subheader("Recent Runs")
st.dataframe(df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Trend chart
# ---------------------------------------------------------------------------
st.subheader("Run Trend")
trend = (
    df.groupby(df["started_at"].dt.floor("H"))["id"]
    .count()
    .reset_index()
    .rename(columns={"id": "runs"})
)
st.line_chart(trend.set_index("started_at"))

# ---------------------------------------------------------------------------
# Run details explorer
# ---------------------------------------------------------------------------
st.subheader("Run Details")
selected_id = st.selectbox("Select a run ID", options=df["id"].tolist())
detail = _run_details_compat(store, selected_id)

left, right = st.columns([2, 1], vertical_alignment="top")

with left:
    # Try to enrich the header from the normalized rows
    selected_row = next((r for r in rows if r["id"] == selected_id), None)
    title = (selected_row or {}).get("name") or detail.get("name") or "Run"
    agent_id = (selected_row or {}).get("agent_id") or detail.get("agent_id")
    recipe_id = (selected_row or {}).get("recipe_id") or detail.get("recipe_id")
    status = (selected_row or {}).get("status") or detail.get("status")
    duration_ms = (selected_row or {}).get("duration_ms") or detail.get("duration_ms") or 0

    st.markdown(f"**{title}** &nbsp;•&nbsp; #{selected_id}")
    st.caption(f"Agent={agent_id} · Recipe={recipe_id} · Status={status} · Duration={int(duration_ms)} ms")

    # Steps
    st.markdown("**Steps**")
    steps = detail.get("steps", [])
    for s in steps:
        level = s.get("level") or "info"
        phase = s.get("phase") or "—"
        msg = s.get("message") or s.get("msg") or "—"
        status = s.get("status") or "—"
        ts = s.get("ts") or s.get("time") or "—"
        with st.expander(f"[{phase}] {msg}  —  {status} · {ts}", expanded=False):
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

# ---------------------------------------------------------------------------
# Workflows panel (from SQLAlchemy DB)
# ---------------------------------------------------------------------------
st.subheader("Workflows")
from core.workflow.service import compute_status  # optional color

with get_session() as db:  # type: ignore
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
