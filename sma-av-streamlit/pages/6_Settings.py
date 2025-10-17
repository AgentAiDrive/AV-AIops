# pages/02_Settings.py (or your Settings file)
import os, streamlit as st
from core.secrets import get_openai_key, get_anthropic_key, is_mock_enabled

st.title("⚙️ Settings")

provider = st.radio("LLM provider", ["OpenAI", "Anthropic"],
    index=0 if st.session_state.get("llm_provider","OpenAI")=="OpenAI" else 1,
    horizontal=True)
st.session_state["llm_provider"] = provider

dot = "🟢" if provider == "OpenAI" else "🔵"
st.caption(f"Active model: {dot} {provider}")

with st.expander("API keys & environment (session overrides; leave blank to keep existing)"):
    # DO NOT prefill secrets; leave blank fields to avoid accidental overwrite
    openai_in = st.text_input("OPENAI_API_KEY (leave blank to keep existing)", type="password", value="")
    anth_in   = st.text_input("ANTHROPIC_API_KEY (leave blank to keep existing)", type="password", value="")
    mock = st.toggle("Mock MCP Tools (no external calls)", value=is_mock_enabled())
    if st.button("Save"):
        # Only save non-empty values to session_state overrides
        if openai_in.strip():
            st.session_state["OPENAI_API_KEY"] = openai_in.strip()
        if anth_in.strip():
            st.session_state["ANTHROPIC_API_KEY"] = anth_in.strip()
        st.session_state["mock_mcp"] = mock
        st.success("Saved (session overrides set; secrets.toml/env remain source of truth).")

with st.expander("Diagnostics"):
    ok, src = get_openai_key()
    ak, asrc = get_anthropic_key()
    st.write({
        "openai_key_found": bool(ok), "openai_source": src,
        "anthropic_key_found": bool(ak), "anthropic_source": asrc,
        "mock_enabled": is_mock_enabled(),
    })
