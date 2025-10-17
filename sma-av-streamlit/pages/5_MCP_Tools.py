
import streamlit as st
import os, json
from core.mcp.scaffold import scaffold

st.title("🧰 MCP Tools")
tools_dir = os.path.join(os.getcwd(), "core", "mcp", "tools")
os.makedirs(tools_dir, exist_ok=True)

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
found = []
for entry in os.scandir(tools_dir):
    if entry.is_dir():
        found.append(entry.name)
if found:
    for t in sorted(found):
        with st.container(border=True):
            st.markdown(f"**{t}**")
            man = os.path.join(tools_dir, t, "manifest.json")
            if os.path.exists(man):
                st.code(open(man, "r", encoding="utf-8").read(), language="json")
else:
    st.info("No tools discovered yet.")

st.subheader("Scaffold New Tool")
name = st.text_input("Tool name (e.g. slack)")
if st.button("Scaffold") and name:
    scaffold(os.getcwd(), name.strip())
    st.success(f"Tool '{name}' scaffolded.")

