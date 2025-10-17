# core/ui/page_tips.py
from __future__ import annotations
import streamlit as st

_TIPS = {
    "Setup Wizard": "Initialize DB, seed demo agents/tools/recipes, and sample workflows. Safe to run multiple times.",
    "Settings": "Choose active LLM (OpenAI↔Anthropic) for Chat/recipes/SOPs. Indicator shows which model is active.",
    "Chat": "Slash commands to generate SOPs → Recipes → Run. Toggle JSON mode for raw payloads.",
    "Agents": "Create agents, choose a recipe, trigger a run. Results appear in Dashboard → Runs.",
    "Recipes": "Author YAML recipes in IPAV format; validate, version, and save to the library.",
    "MCP Tools": "Discover local connectors (slack/zoom/servicenow). Check `/health` and call `/action` with JSON body.",
    "Workflows": "Wire Agent + Recipe + Trigger (manual/interval). Every run records IPAV steps & artifacts.",
    "Dashboard": "KPIs (runs, success %, p95 duration), trends, and run details (steps + artifacts).",
}

def show(page_key: str, icon: str = "💡") -> None:
    """Show a compact page tip at the top of any page."""
    text = _TIPS.get(page_key)
    if text:
        st.info(f"{icon} {text}")
