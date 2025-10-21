# pages/5_MCP_Tools.py (example filename)
import json
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple

import requests
import streamlit as st

from core.mcp.scaffold import scaffold
from core.ui.page_tips import show as show_tip

PAGE_KEY = "MCP Tools"
show_tip(PAGE_KEY)

st.title("🧰 MCP Tools")
tools_dir = Path(os.getcwd()) / "core" / "mcp" / "tools"
tools_dir.mkdir(parents=True, exist_ok=True)
st.caption("Sample connectors provided for calendars, Q-SYS/Extron devices, and incident ticketing.")
st.caption("You must add the token to the Streamlit secrets folder — contact admin for assistance.")

# --------------------------------------------------------------------------------------
# Token resolution from Streamlit secrets
# --------------------------------------------------------------------------------------
# We try a few sensible locations so you don't have to rename your secrets if you
# already have them. Order of precedence (first hit wins):
#  1. st.secrets["mcp"][<service_key>]["api_key"]
#  2. st.secrets["mcp"][<service_key>]
#  3. st.secrets[<CANONICAL_SECRET_NAME>]
#  4. st.secrets["tokens"][<service_key>]
#  5. st.secrets[<service_key>] (string)
#
# For convenience, we also export the resolved token to os.environ under a canonical
# ENV name so scaffolded tools that still read env vars continue to work.
CANONICAL = {
    "Slack":       ("SLACK_BOT_TOKEN",        "slack"),
    "Zoom":        ("ZOOM_JWT",               "zoom"),
    "ServiceNow":  ("SERVICENOW_API_KEY",     "servicenow"),
    "Zendesk":     ("ZENDESK_TOKEN",          "zendesk"),
    "Teams":       ("MS_GRAPH_TOKEN",         "teams"),
    "Webex":       ("WEBEX_TOKEN",            "webex"),
    "Q-SYS":       ("QSYS_API_KEY",           "q-sys"),
    "Extron":      ("EXTRON_API_KEY",         "extron"),
    "Custom":      ("CUSTOM_TOKEN",           "custom"),
}

def _mask(s: Optional[str]) -> str:
    if not s:
        return "missing"
    return "••••" + (s[-4:] if len(s) >= 4 else "••••")

def resolve_token(service_type: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Return (token, env_name, source_desc) for the given service_type using Streamlit secrets.
    """
    env_name, key = CANONICAL.get(service_type, ("CUSTOM_TOKEN", "custom"))
    svc = key  # lower service key

    # Try the different secret locations
    try_paths = []
    if "mcp" in st.secrets:
        mcp = st.secrets.get("mcp", {})
        if isinstance(mcp, dict):
            # mcp.<svc>.api_key
            if svc in mcp and isinstance(mcp[svc], dict) and "api_key" in mcp[svc]:
                return mcp[svc]["api_key"], env_name, f"st.secrets['mcp']['{svc}']['api_key']"
            # mcp.<svc> (string)
            if svc in mcp and isinstance(mcp[svc], str):
                return mcp[svc], env_name, f"st.secrets['mcp']['{svc}']"

    if env_name in st.secrets:
        return st.secrets[env_name], env_name, f"st.secrets['{env_name}']"

    if "tokens" in st.secrets and isinstance(st.secrets["tokens"], dict) and svc in st.secrets["tokens"]:
        return st.secrets["tokens"][svc], env_name, f"st.secrets['tokens']['{svc}']"

    if svc in st.secrets and isinstance(st.secrets[svc], str):
        return st.secrets[svc], env_name, f"st.secrets['{svc}']"

    return None, env_name, None

def ensure_env_for_service(service_type: str) -> Tuple[Optional[str], Optional[str]]:
    token, env_name, source = resolve_token(service_type)
    if token and env_name:
        os.environ[env_name] = token  # keep legacy env-var flows working (e.g., MCPD, scaffolds)
    return token, source

# --------------------------------------------------------------------------------------
# Health cards (optional reachability)
# --------------------------------------------------------------------------------------
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

# --------------------------------------------------------------------------------------
# Discovered tools + delete action
# --------------------------------------------------------------------------------------
st.subheader("Discovered Tools")
found = [entry for entry in tools_dir.iterdir() if entry.is_dir()]
if found:
    for t in sorted(found, key=lambda p: p.name):
        manifest_path = t / "manifest.json"
        readme_path = t / "README.md"
        with st.container(border=True):
            head_cols = st.columns([4, 1.2, 1.2])
            head_cols[0].markdown(f"**{t.name}**")
            # Delete button (safe; asks confirm)
            with head_cols[1]:
                if st.button("Delete", key=f"del_{t.name}"):
                    st.session_state[f"confirm_del_{t.name}"] = True
            with head_cols[2]:
                if st.session_state.get(f"confirm_del_{t.name}"):
                    if st.button("Confirm ❗", key=f"confirm2_{t.name}"):
                        try:
                            shutil.rmtree(t)
                            st.success(f"Deleted tool '{t.name}'.")
                            st.session_state.pop(f"confirm_del_{t.name}", None)
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Delete failed: {e}")

            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    st.json(manifest)
                    # optional: surface a /health if manifest declares it
                    base_url = manifest.get("base_url") or manifest.get("server", {}).get("base_url")
                    if base_url:
                        with st.expander("Health check", expanded=False):
                            health_card(t.name, base_url)
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

# --------------------------------------------------------------------------------------
# Scaffold (uses secrets; no username/password OAuth)
# --------------------------------------------------------------------------------------
st.subheader("Scaffold New Tool")
name = st.text_input("Tool name (e.g. slack)")

service_type = st.selectbox(
    "Service type",
    ["Slack", "Zoom", "ServiceNow", "Zendesk", "Teams", "Webex", "Q-SYS", "Extron", "Custom"],
    index=0,
)

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

# Inform the user which secret key we will look for and export to env
token, token_source = ensure_env_for_service(service_type)
env_name, _ = CANONICAL.get(service_type, ("CUSTOM_TOKEN", "custom"))
st.caption(
    f"Auth: using **Streamlit secrets → {_mask(token)}** "
    + (f"(source: `{token_source}`)" if token_source else "(not found)")
    + f" • exported to `os.environ['{env_name}']`"
)

# ✅ Special case: ServiceNow — use API key from secrets (no username/password OAuth)
if service_type == "ServiceNow":
    st.info(
        "ServiceNow will be scaffolded to use a **Bearer API token** from Streamlit secrets "
        "(no username/password OAuth)."
    )

# Optional scopes JSON
scopes_json = st.text_area(
    "Action scopes (JSON)",
    placeholder='{"actions": ["send_message"]}',
    help="List of action endpoint names, as JSON. Example: {\"actions\": [\"send_message\", \"create_ticket\"]}",
)

cols = st.columns(2)
if cols[0].button("Scaffold") and name:
    try:
        # Pass the canonical ENV name through to the scaffold so generated code knows which
        # environment variable to read. We already exported the token value to that ENV above.
        token_env = CANONICAL.get(service_type, ("CUSTOM_TOKEN", "custom"))[0]
        scaffold(
            os.getcwd(),
            name.strip(),
            service_type=service_type,
            base_url=base_url,
            token_env=token_env,
            scopes_json=scopes_json,
        )
        st.success(f"Tool '{name}' scaffolded with {service_type} template (auth via Streamlit secrets → env).")
    except Exception as ex:
        st.error(str(ex))

if cols[1].button("Recheck secrets"):
    # Force re-resolution and re-export to env
    token, token_source = ensure_env_for_service(service_type)
    st.toast(f"Resolved {service_type} token: {('OK ' + _mask(token)) if token else 'missing'}")
