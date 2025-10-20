import json
import os
from pathlib import Path

import streamlit as st
import requests

from core.mcp.scaffold import scaffold
from core.ui.page_tips import show as show_tip

# The MCP Tools page lists existing connectors and scaffolds new ones.
# In addition to the name, this revised version collects service type,
# default base URL, environment variable for the API token, and action scopes
# from the user.  It then passes these values to the enhanced scaffold
# function to generate a functional connector skeleton.

PAGE_KEY = "MCP Tools"
show_tip(PAGE_KEY)

st.title("🧰 MCP Tools")
tools_dir = Path(os.getcwd()) / "core" / "mcp" / "tools"
tools_dir.mkdir(parents=True, exist_ok=True)
st.caption("Sample connectors provided for calendars, Q-SYS/Extron devices, and incident ticketing.")


def health_card(name: str, base_url: str):
    """Render a card showing the health of a discovered MCP tool."""
    try:
        r = requests.get(f"{base_url}/health", timeout=3)
        ok = r.ok and r.json().get("ok", False)
        dot = "🟢" if ok else "🔴"
        st.markdown(f"**{name}** {dot}")
        st.code(r.json(), language="json")
    except Exception as e:
        st.markdown(f"**{name}** 🔴")
        st.caption(str(e))


# Example usage (commented):
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

# Display a readme for guidance if present
sample_readme = tools_dir / "README.md"
if sample_readme.exists():
    with st.expander("How to build custom MCP tools", expanded=False):
        st.markdown(sample_readme.read_text(encoding="utf-8"))


st.subheader("Scaffold New Tool")
name = st.text_input("Tool name (e.g. slack)")
# Choose a service type to pre-populate defaults
service_type = st.selectbox(
    "Service type",
    [
        "Slack",
        "Zoom",
        "ServiceNow",
        "Zendesk",
        "Teams",
        "Webex",
        "Q-SYS",
        "Extron",
        "Custom",
    ],
    index=0,
)
# Default base URLs for known services
default_base = {
    "Slack": "https://slack.com/api",
    "Zoom": "https://api.zoom.us/v2",
    "ServiceNow": "https://your_instance.service-now.com",
    "Zendesk": "https://your_company.zendesk.com/api/v2",
    "Teams": "https://graph.microsoft.com/v1.0",
    "Webex": "https://webexapis.com/v1",
    "Q-SYS": "https://qsys-controller.local",
    "Extron": "https://extron-controller.local",
    "Custom": "",
}
base_url = st.text_input("Base URL", value=default_base.get(service_type, ""))
# Default environment variable names for API tokens
token_defaults = {
    "Slack": "SLACK_BOT_TOKEN",
    "Zoom": "ZOOM_JWT",
    "ServiceNow": "SN_TOKEN",
    "Zendesk": "ZENDESK_TOKEN",
    "Teams": "MS_GRAPH_TOKEN",
    "Webex": "WEBEX_TOKEN",
    "Q-SYS": "QSYS_API_KEY",
    "Extron": "EXTRON_API_KEY",
    "Custom": "CUSTOM_TOKEN",
}
token_env = st.text_input("Env var for API token", value=token_defaults.get(service_type, ""))
# JSON text area for actions; optional
scopes_json = st.text_area(
    "Action scopes (JSON)",
    placeholder='{"actions": ["send_message"]}',
    help="List of action endpoint names, as JSON. Example: {\"actions\": [\"send_message\", \"create_ticket\"]}",
)

# When the button is clicked, call scaffold with collected parameters
if st.button("Scaffold") and name:
    try:
        scaffold(
            os.getcwd(),
            name.strip(),
            service_type=service_type,
            base_url=base_url,
            token_env=token_env,
            scopes_json=scopes_json,
        )
        st.success(f"Tool '{name}' scaffolded with {service_type} template.")
    except Exception as ex:
        st.error(str(ex))
