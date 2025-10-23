from __future__ import annotations
import re
from pathlib import Path
from io import BytesIO
import requests
from PIL import Image, UnidentifiedImageError
import streamlit as st
from core.db.seed import init_db

# ---------- Icon: fetch from GitHub user-attachments BEFORE any st.* calls ----------
LOGO_URL = "https://github.com/user-attachments/assets/00c68a1d-224f-4170-b44f-9982bf4b5e8d"

ICON_URL = "https://raw.githubusercontent.com/AgentAiDrive/AV-AIops/refs/heads/IPAV-Agents/sma-av-streamlit/ipav.ico"

def _fetch_pil_image(url: str) -> Image.Image | None:
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content))
        img.load()  # force load to avoid lazy issues
        return img
    except (requests.RequestException, UnidentifiedImageError, OSError):
        return None

_icon_img = _fetch_pil_image(ICON_URL)

# ---------- Page config (must be first Streamlit command) ----------

st.set_page_config(page_title="Agentic Ops IPAV", page_icon= _icon_img, layout="wide")

# ---------- Header ----------
st.image(LOGO_URL, caption="", width=293)
st.title("Agentic Ops - IPAV SOP Workflow Orchestration")
# Show the same image under the title (keeps README width ≈93)
st.write("Use sidebar to navigate.")

def model_light():
    p = (st.session_state.get("llm_provider") or "OpenAI")
    dot = "🟢" if p == "OpenAI" else "🔵"
    st.sidebar.markdown(f"**Model**: {dot} {p}")

model_light()

st.success("Database seeded & initialized.")
st.title("Support")
try:
    from core.ui.page_tips import PAGE_TIPS  # type: ignore
except Exception:
    PAGE_TIPS = {
        "Setup Wizard": (
            "Initialize DB and seed demo content: fixed system agents (Baseline, EventForm, Intake, Plan, Act, Verify, Learn),"
            "sample Orchestrator + Fixed-Agent recipes, and mock MCP tools. Idempotent—safe to run multiple times."
        ),
        "Settings": (
            "Select active LLM provider (OpenAI ↔ Anthropic). Shows key source and MCP mock status."
            "No silent fallback—set a valid API key in secrets/env."
        ),
        "Chat": (
            "Use slash commands. **/sop** now compiles an Orchestrator recipe **plus** bound Fixed-Agent recipes from the SOP, "
            "scaffolds required MCP tools, attaches to the chosen agent, and can execute the run. "
            "Toggle JSON mode to view raw tool payloads."
        ),
        "Agents": (
            "Manage agents. Fixed system agents are non-editable and enforce guardrails; user-created agents hold domain recipes. "
            "Attach recipes and trigger runs with approvals where required."
        ),
        "Recipes": (
            "Author and manage recipes. Library includes **Orchestrator** recipes (workflow ‘what’) and **Fixed-Agent** recipes "
            "(phase ‘how’ for Intake/Plan/Act/Verify/Learn). Validate, version, and save."
        ),
        "MCP Tools": (
            "Discover local connectors (Slack/Zoom/ServiceNow/Q-SYS/etc.). Run `/health` and `/action` with JSON. "
            "Shows allow-listed methods; /sop can auto-scaffold tools referenced by the SOP."
        ),
        "Workflows": (
            "Wire **Orchestrator + Agent + Trigger** (manual or interval). Approvals gate risky steps. "
            "Each run records the full IPAV→L sequence with artifacts and evidence."
        ),
        "Dashboard": (
            "KPIs and trends: runs, success %, p95 duration, First-Time-Right, MTTR, automation %. "
            "Drill into Run Details for steps, approvals, evidence, and links to generated KB articles."
        ),
    }

# ---------------- Path resolution (robust) ----------------
def find_repo_root() -> Path:
    """Walk up from this file to find the app root (where app.py / core / pages live)."""
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "app.py").exists() or (p / "core").is_dir():
            return p
    return Path.cwd()

APP_ROOT = find_repo_root()
CWD = Path.cwd()

candidates = [
    APP_ROOT / "docs" / "RUNBOOK.md",
    APP_ROOT / "RUNBOOK.md",
    CWD / "docs" / "RUNBOOK.md",
    CWD / "RUNBOOK.md",
]
runbook_path = next((p for p in candidates if p.exists()), None)

# ---------------- Load runbook text ----------------
if not runbook_path:
    st.warning("RUNBOOK.md not found. Showing a minimal placeholder.")
    runbook_md = """# SMA AV-AI Ops — Runbook (Placeholder)

Please add your full runbook at `docs/RUNBOOK.md` (preferred) or project root `RUNBOOK.md`.
"""
else:
    runbook_md = runbook_path.read_text(encoding="utf-8")
    st.success(f"Loaded runbook: `{runbook_path}`")

# ---------------- Global tips summary ----------------
with st.expander("Global Page Tips (quick reference)", expanded=False):
    cols = st.columns(2)
    keys = list(PAGE_TIPS.keys())
    for i, k in enumerate(keys):
        with cols[i % 2]:
            st.markdown(f"**{k}**")
            st.caption(PAGE_TIPS[k])

st.divider()

# ---------------- TOC builder ----------------
def build_toc(md: str):
    lines = md.splitlines()
    items = []
    for ln in lines:
        m = re.match(r"^(#{1,3})\s+(.*)", ln)
        if not m:
            continue
        level = len(m.group(1))
        title = m.group(2).strip()
        anchor = re.sub(r"[^\w\- ]", "", title).strip().lower().replace(" ", "-")
        items.append((level, title, anchor))
    return items

toc = build_toc(runbook_md)

# ---------------- Search & render ----------------
q = st.text_input("Search the runbook", value="", placeholder="type to filter headings & body...")
filtered_md = runbook_md
if q.strip():
    pat = re.compile(re.escape(q), re.IGNORECASE)
    filtered_md = pat.sub(lambda m: f"**{m.group(0)}**", runbook_md)

with st.expander("Table of Contents", expanded=False):
    if not toc:
        st.caption("No headings found.")
    else:
        for level, title, anchor in toc:
            indent = "&nbsp;" * (level - 1) * 4
            st.markdown(f"{indent}• [{title}](#{anchor})", unsafe_allow_html=True)

st.download_button("Download RUNBOOK.md", data=runbook_md, file_name="RUNBOOK.md", mime="text/markdown")

st.divider()
st.markdown(filtered_md, unsafe_allow_html=False)

# ---------------- Optional debug (moved to bottom) ----------------
def _get_query_params():
    try:
        # Newer Streamlit
        return dict(st.query_params)
    except Exception:
        # Back-compat
        return st.experimental_get_query_params()  # type: ignore[attr-defined]

qp = _get_query_params()
debug_on = str(qp.get("debug", ["0"])[0]).lower() in ("1", "true", "yes")

with st.expander("Debug: where I'm looking for RUNBOOK.md", expanded=debug_on):
    st.caption(f"App root resolved to: `{APP_ROOT}`")
    st.caption(f"Working dir: `{CWD}`")
    st.code("\n".join(str(c) for c in candidates), language="text")

init_db()
