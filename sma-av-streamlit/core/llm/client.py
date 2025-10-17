
from __future__ import annotations
from typing import List, Dict
import streamlit as st

def _mock_reply(messages: List[Dict], json_mode: bool) -> str:
    last = messages[-1]["content"] if messages else ""
    if json_mode:
        return '{"reply": "This is a demo JSON reply", "echo": %s}' % repr(last)
    return f"(demo) You said: {last[:200]}"

def chat(messages: List[Dict], json_mode: bool = False) -> str:
    provider = st.secrets.get("DEFAULT_MODEL_PROVIDER", "openai")
    if provider == "anthropic" and st.secrets.get("ANTHROPIC_API_KEY"):
        from .providers.anthropic_client import chat_claude
        return chat_claude(st.secrets["ANTHROPIC_API_KEY"], messages)
    if st.secrets.get("OPENAI_API_KEY"):
        from .providers.openai_client import chat_openai
        return chat_openai(st.secrets["OPENAI_API_KEY"], messages)
    return _mock_reply(messages, json_mode)
