# sma-av-streamlit/pages/07_Dashboard.py
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import streamlit as st
from core.runs_store import RunStore

st.set_page_config(page_title="Dashboard", layout="wide")

st.title("Dashboard")
st.caption("AV AI OPS — Dashboard. Live view of workflow runs, steps, artifacts, and KPIs.")

# Store init
db_path = Path(__file__).resolve().parents[1] / "avops.db"
store = RunStore(db_path=db_path)

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    win = st.selectbox("Time window", ["24h", "7d", "30d", "All"], index=0)
    statuses = st.multiselect("Status", ["running", "success", "failed"], default=["running", "success", "failed"])
    auto = st.toggle("Auto-refresh (5s)", value=False)

if auto:
    st.experimental_set_query_params(_=datetime.now().timestamp())  # avoid cache
    st.autorefresh = st.rerun  # noop compatibility

since = None
now = datetime.now(timezone.utc)
if win == "24h":
    since = now - timedelta(hours=24)
elif win == "7d":
    since = now - timedelta(days=7)
elif win == "30d":
    since = now - timedelta(days=30)

# KPIs
stats = store.stats(since=since)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Runs", f"{stats['runs']}")
c2.metric("Success rate", f"{stats['success_rate']:.1f}%")
c3.metric("p95 duration", f"{stats['p95_ms']:.0f} ms")
c4.metric("Last error", stats['last_error'] or "—")

# Latest runs table
rows = store.latest_runs(limit=200, status=statuses)
if since:
    rows = [r for r in rows if r["started_at"] >= since.isoformat()]

if not rows:
    st.info("No runs yet. Trigger a workflow from the **Workflows** page.")
    st.stop()

df = pd.DataFrame(rows)
df["started_at"] = pd.to_datetime(df["started_at"])
df["finished_at"] = pd.to_datetime(df["finished_at"])
df_display = df[["id", "name", "status", "trigger", "agent_id", "recipe_id", "duration_ms", "started_at"]].copy()
df_display.rename(columns={"duration_ms": "duration (ms)"}, inplace=True)

st.subheader("Recent Runs")
st.dataframe(df_display, use_container_width=True, hide_index=True)

# Trend chart
st.subheader("Run Trend")
trend = df.groupby(df["started_at"].dt.floor("H"))["id"].count().reset_index()
trend.rename(columns={"id": "runs"}, inplace=True)
st.line_chart(trend.set_index("started_at"))

# Run details explorer
st.subheader("Run Details")
selected_id = st.selectbox("Select a run ID", options=df_display["id"].tolist())
detail = store.run_details(selected_id)

left, right = st.columns([2, 1], vertical_alignment="top")

with left:
    st.markdown(f"**{detail.get('name','')}** &nbsp;•&nbsp; #{detail.get('id')}")
    st.caption(f"Agent={detail.get('agent_id')} · Recipe={detail.get('recipe_id')} · "
               f"Status={detail.get('status')} · Duration={int(detail.get('duration_ms') or 0)} ms")
    # Steps
    st.markdown("**Steps**")
    for s in detail.get("steps", []):
        color = {"info":"gray","warn":"orange","error":"red"}.get(s["level"], "gray")
        with st.expander(f"[{s['phase']}] {s['message']}  —  {s['status']} · {s['ts']}", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Payload**")
                st.json(s["payload"] or {})
            with c2:
                st.markdown("**Result**")
                st.json(s["result"] or {})

with right:
    st.markdown("**Artifacts**")
    arts = detail.get("artifacts", [])
    if not arts:
        st.write("—")
    else:
        for a in arts:
            with st.container(border=True):
                st.write(f"**{a['kind']}** — {a.get('title') or ''}")
                if a.get("url"):
                    st.write(a["url"])
                if a.get("external_id"):
                    st.caption(f"id: {a['external_id']}")
                if a.get("data"):
                    st.json(a["data"])

store = RunStore()  # same file/path as in service.py

colA, colB = st.columns([2,1])
with colA:
    hours = st.slider("Window (hours)", 1, 168, 24)
with colB:
    limit = st.number_input("Show recent runs", min_value=5, max_value=100, value=20, step=5)

stats = store.stats(hours=hours)
st.metric("Runs", stats["runs"])
st.metric("Success %", f"{stats['success_rate']:.1f}%")
st.metric("p95 duration (s)", f"{stats['p95_s']:.2f}")

st.subheader("Recent Runs")
for r in store.recent(limit=limit, hours=hours):
    badge = "🟢" if r["ok"] else "🔴"
    title = r.get("title") or "Run"
    meta = r.get("meta", {})
    wf = meta.get("workflow_name") or meta.get("workflow_id")
    st.markdown(
        f"{badge} **{title}**"
        + (f" · _{wf}_" if wf else "")
        + f" · {r['started_at']} → {r['finished_at']} ({r['duration_s']:.2f}s)"
    )
    if meta:
        with st.expander("Meta"):
            st.json(meta)
    if r.get("error"):
        st.error(r["error"])

st.subheader("Workflows")
with get_session() as db:  # type: ignore
    wfs = list_workflows(db)
    if not wfs:
        st.info("No workflows defined yet.")
    for wf in wfs:
        status_color = {"green":"🟢","yellow":"🟡","red":"🔴"}.get(wf.enabled and "green" or "red", "🟡")
        st.markdown(
            f"{status_color} **{wf.name}** · Agent `{wf.agent_id}` · Recipe `{wf.recipe_id}`"
            f"<br/>Last: {wf.last_run_at or '—'} · Next: {wf.next_run_at or '—'}",
            unsafe_allow_html=True
        )
