# pages/6_Settings.py
import os
import streamlit as st

from core.secrets import (
    get_openai_key,
    get_anthropic_key,
    is_mock_enabled,
    get_active_key,
    pick_active_provider,
)
from core.llm.client import refresh_client, whoami
# paste this at the top of any page
import streamlit as st
from core.ui.page_tips import show as show_tip

PAGE_KEY = "Settings"  # <= change per page: "Setup Wizard" | "Settings" | "Chat" | "Agents" | "Recipes" | "MCP Tools" | "Workflows" | "Dashboard"
show_tip(PAGE_KEY)

st.title("⚙️ Settings")

# ---- provider select --------------------------------------------------------
prev = st.session_state.get("llm_provider", "OpenAI")
provider = st.radio(
    "LLM provider",
    ["OpenAI", "Anthropic"],
    index=0 if prev == "OpenAI" else 1,
    horizontal=True,
)
st.session_state["llm_provider"] = provider

# refresh client if provider changed
if prev != provider:
    refresh_client()

dot = "🟢" if provider == "OpenAI" else "🔵"
st.caption(f"Active model: {dot} {provider}")

# ---- secrets & overrides (safe) --------------------------------------------
with st.expander("API keys & environment (session overrides; leave blank to keep existing)", expanded=False):
    openai_in = st.text_input("OPENAI_API_KEY (leave blank to keep existing)", type="password", value="")
    anth_in   = st.text_input("ANTHROPIC_API_KEY (leave blank to keep existing)", type="password", value="")
    mock = st.toggle("Mock MCP Tools (no external calls)", value=is_mock_enabled())

    cols = st.columns(3)
    if cols[0].button("Save"):
        # Only set overrides when non-empty; never store blanks.
        if openai_in.strip():
            st.session_state["OPENAI_API_KEY"] = openai_in.strip()
        if anth_in.strip():
            st.session_state["ANTHROPIC_API_KEY"] = anth_in.strip()
        st.session_state["mock_mcp"] = mock
        refresh_client()
        st.success("Saved session overrides. (secrets/env remain canonical)")

    if cols[1].button("Clear overrides"):
        for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
            if k in st.session_state:
                del st.session_state[k]
        refresh_client()
        st.info("Session overrides cleared.")

    # Optional: set default model IDs via env (used by client)
    with cols[2]:
        st.caption("Model IDs (optional)")
    oai_model = st.text_input("OPENAI_MODEL", value=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    claude_model = st.text_input("ANTHROPIC_MODEL", value=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620"))
    if st.button("Apply model IDs"):
        os.environ["OPENAI_MODEL"] = oai_model.strip()
        os.environ["ANTHROPIC_MODEL"] = claude_model.strip()
        st.success("Model IDs updated for this session.")
        refresh_client()

# ---- diagnostics ------------------------------------------------------------
with st.expander("Diagnostics", expanded=True):
    ok, src = get_openai_key()
    ak, asrc = get_anthropic_key()
    active_key, active_provider, active_src = get_active_key()
    st.write({
        "openai_key_found": bool(ok),
        "openai_source": src,
        "anthropic_key_found": bool(ak),
        "anthropic_source": asrc,
        "selected_provider": provider,
        "resolved_provider": active_provider,
        "active_key_source": active_src,
        "mock_enabled": is_mock_enabled(),
    })

    # Runtime client identity (forces build if possible)
    cols = st.columns(2)
    if cols[0].button("Who am I? (LLM client)"):
        try:
            info = whoami()
            st.success("Client ready")
            st.json(info)
        except Exception as e:
            st.error(f"Client not ready: {type(e).__name__}: {e}")

    # Smoke test a tiny call via Chat page's client (optional)
    if cols[1].button("Test minimal prompt"):
        try:
            # Defer actual call to Chat page—this is just a readiness probe through whoami()
            info = whoami()
            st.success(f"Client OK: {info}")
        except Exception as e:
            st.error(f"LLM test failed: {type(e).__name__}: {e}")
