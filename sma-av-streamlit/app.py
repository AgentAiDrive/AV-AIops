import streamlit as st
from core.db.seed import init_db

st.set_page_config(page_title="SMA AV-AI Ops", page_icon="🎛️", layout="wide")
st.title("SMA AV‑AI Ops Orchestration (Streamlit)")
st.write("Use sidebar to navigate.")

def model_light():
    p = (st.session_state.get("llm_provider") or "OpenAI")
    dot = "🟢" if p == "OpenAI" else "🔵"
    st.sidebar.markdown(f"**Model**: {dot} {p}")

model_light()

st.success("Database initialized.")
init_db()
