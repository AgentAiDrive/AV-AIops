import os, streamlit as st

st.title("⚙️ Settings")

# Persist provider in session + local cache
provider = st.radio(
    "LLM provider",
    ["OpenAI", "Anthropic"],
    index=0 if st.session_state.get("llm_provider", "OpenAI") == "OpenAI" else 1,
    horizontal=True,
    help="Choose which model to use for Chat and recipe/SOP generation.",
)
st.session_state["llm_provider"] = provider

dot = "🟢" if provider == "OpenAI" else "🔵"
st.caption(f"Active model: {dot} {provider}")

with st.expander("API keys & environment"):
    openai = st.text_input("OPENAI_API_KEY", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    anthropic = st.text_input("ANTHROPIC_API_KEY", type="password", value=os.getenv("ANTHROPIC_API_KEY", ""))
    mock = st.toggle("Mock MCP Tools (no external calls)", value=st.session_state.get("mock_mcp", True))
    if st.button("Save"):
        st.session_state["OPENAI_API_KEY"] = openai
        st.session_state["ANTHROPIC_API_KEY"] = anthropic
        st.session_state["mock_mcp"] = mock
        st.success("Saved in session. (Tip: store keys in .env for persistence)")
