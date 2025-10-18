
import json
import os
from pathlib import Path

import streamlit as st
import requests

from core.mcp.scaffold import scaffold
# paste this at the top of any page
from core.ui.page_tips import show as show_tip

PAGE_KEY = "MCP Tools"  # <= change per page: "Setup Wizard" | "Settings" | "Chat" | "Agents" | "Recipes" | "MCP Tools" | "Workflows" | "Dashboard"
show_tip(PAGE_KEY)

st.title("🧰 MCP Tools")
tools_dir = Path(os.getcwd()) / "core" / "mcp" / "tools"
tools_dir.mkdir(parents=True, exist_ok=True)
st.caption("Sample connectors provided for calendars, Q-SYS/Extron devices, and incident ticketing.")

def health_card(name: str, base_url: str):
    try:
        r = requests.get(f"{base_url}/health", timeout=3)
        ok = r.ok and r.json().get("ok", False)
        dot = "🟢" if ok else "🔴"
        st.markdown(f"**{name}** {dot}")
        st.code(r.json(), language="json")
    except Exception as e:
        st.markdown(f"**{name}** 🔴")
        st.caption(str(e))

# Example:
# health_card("ServiceNow", "http://localhost:8903")
# health_card("Slack", "http://localhost:8901")
# health_card("Zoom", "http://localhost:8902")

st.subheader("Discovered Tools")
found = [entry for entry in tools_dir.iterdir() if entry.is_dir()]
if found:
    for t in sorted(found, key=lambda p: p.name):
        manifest_path = t / "manifest.json"
        readme_path = t / "README.md"
        with st.container(border=True):
            st.markdown(f"**{t.name}**")
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    st.json(manifest)
                except Exception as e:
                    st.error(f"Failed to parse manifest: {e}")
            if readme_path.exists():
                with st.expander("View notes"):
                    st.markdown(readme_path.read_text(encoding="utf-8"))
else:
    st.info("No tools discovered yet.")

sample_readme = tools_dir / "README.md"
if sample_readme.exists():
    with st.expander("How to build custom MCP tools", expanded=False):
        st.markdown(sample_readme.read_text(encoding="utf-8"))

st.subheader("Scaffold New Tool")
name = st.text_input("Tool name (e.g. slack)")
if st.button("Scaffold") and name:
    scaffold(os.getcwd(), name.strip())
    st.success(f"Tool '{name}' scaffolded.")

