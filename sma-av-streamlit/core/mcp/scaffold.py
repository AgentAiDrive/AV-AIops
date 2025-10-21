# core/mcp/scaffold.py
from __future__ import annotations
import os
import json
import textwrap

def scaffold(
    base_dir: str,
    tool_name: str,
    service_type: str = "",
    base_url: str = "",
    token_env: str = "",
    scopes_json: str = "",
    *,  # new kwargs below are optional/backward-compatible
    secrets_source: str = "streamlit_secrets",   # documents where the token *should* come from
    auth_type: str = "bearer",                   # most MCPs here use bearer tokens
) -> None:
    """Generate a new MCP tool with a manifest and example implementation.

    The scaffold writes a manifest file, README, and a Python module implementing
    health and action endpoints.  Supported service types include Slack, Zoom,
    ServiceNow/Zendesk, Q-SYS/Extron, and a generic fallback.  The scopes_json
    argument should contain a JSON object with an "actions" array to specify
    which endpoints to create.  Tokens are pulled from environment variables or
    Streamlit secrets as specified by token_env.
    """
    tools_dir = os.path.join(base_dir, "core", "mcp", "tools")
    os.makedirs(tools_dir, exist_ok=True)
    dest = os.path.join(tools_dir, tool_name)
    os.makedirs(dest, exist_ok=True)

    # Parse the scopes JSON into a dictionary
    try:
        scopes = json.loads(scopes_json) if scopes_json else {"actions": []}
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in scopes: {exc}")

    # ---- Manifest with explicit auth metadata --------------------------------
    # NOTE: This does not change runtime behavior; it documents the contract so
    # UIs/automation can discover auth requirements and give users guidance.
    manifest = {
        "name": tool_name,
        "type": service_type,
        "description": f"Connector for {service_type}",
        "endpoints": ["/health"] + [f"/{action}" for action in scopes.get("actions", [])],
        "base_url": base_url,
        "actions": scopes.get("actions", []),
        # Back-compat hint for older code that looked for token_env:
        "token_env": token_env,
        # New explicit auth block:
        "auth": {
            "type": auth_type,          # usually "bearer"
            "env": token_env,           # e.g., "SERVICENOW_API_KEY"
            "source": secrets_source,   # e.g., "streamlit_secrets"
        },
    }
    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # ---- README: document the secrets → env pattern --------------------------
    readme_text = textwrap.dedent(
        f"""
        # {service_type} Connector

        This connector integrates the application with the {service_type} API.

        **Authentication**
        - Type: `{auth_type}`
        - Env var: `{token_env}`
        - Source: `{secrets_source}` (the app exports the secret to the env var at runtime)

        Add your token in `.streamlit/secrets.toml` and the app will export it to `{token_env}`.
        Example secrets structure (any of the following are acceptable per your app's resolution order):

        ```toml
        # .streamlit/secrets.toml
        [{secrets_source if '.' not in secrets_source else secrets_source.split('.')[0]}]
        # Example buckets your app resolves, e.g.:
        # [mcp.servicenow]
        # api_key = "sn_xxx..."
        # or a flat key:
        {token_env} = "your-token-here"
        ```

        The `/health` endpoint calls a simple API method to verify connectivity,
        and each action endpoint implements one automation action.
        """
    ).strip()
    with open(os.path.join(dest, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_text + "\n")

    # ---- Choose a template for the implementation ----------------------------
    impl_path = os.path.join(dest, f"{tool_name}.py")
    service_key = (service_type or "").lower()
    if service_key == "slack":
        code = _slack_template(base_url, token_env, scopes.get("actions", []))
    elif service_key == "zoom":
        code = _zoom_template(base_url, token_env, scopes.get("actions", []))
    elif service_key in {"servicenow", "zendesk"}:
        code = _ticketing_template(service_type, base_url, token_env, scopes.get("actions", []))
    elif service_key in {"q-sys", "extron"}:
        code = _device_template(service_type, base_url, token_env, scopes.get("actions", []))
    else:
        code = _generic_template(service_type, base_url, token_env, scopes.get("actions", []))
    with open(impl_path, "w", encoding="utf-8") as f:
        f.write(code)

# ---------------------------------------------------------------------------
# Template functions
# These functions build the Python source for each type of connector.
# They return a complete source file as a string.

def _slack_template(base_url: str, token_env: str, actions: list[str]) -> str:
    """Generate a Slack connector."""
    base = base_url or "https://slack.com/api"
    header = f'''"""
Slack Connector auto-generated by AIOps scaffolder.
"""
import os
import requests

BASE_URL = "{base}"
TOKEN_ENV = "{token_env}"

def health() -> dict:
    """Check Slack authentication by calling `auth.test`."""
    token = os.getenv(TOKEN_ENV, "")
    resp = requests.post(f"{{BASE_URL}}/auth.test", headers={{"Authorization": f"Bearer {{token}}"}})
    try:
        data = resp.json()
    except Exception:
        data = {{}}
    return {{"ok": bool(resp.ok), "data": data}}
'''
    action_code = ""
    for action in actions or []:
        action_code += f"""

def {action}(payload: dict) -> dict:
    \"\"\"Call Slack API endpoint '{action}'.\"\"\"
    token = os.getenv(TOKEN_ENV, "")
    url = f"{{BASE_URL}}/{action}"
    resp = requests.post(url, headers={{"Authorization": f"Bearer {{token}}" }}, json=payload)
    try:
        return resp.json()
    except Exception:
        return {{}}
"""
    return (header + action_code).rstrip()

def _zoom_template(base_url: str, token_env: str, actions: list[str]) -> str:
    """Generate a Zoom connector."""
    base = base_url or "https://api.zoom.us/v2"
    header = f'''"""
Zoom Connector auto-generated by AIOps scaffolder.
"""
import os
import requests

BASE_URL = "{base}"
TOKEN_ENV = "{token_env}"

def health() -> dict:
    """Check Zoom connectivity by retrieving the current user's profile."""
    token = os.getenv(TOKEN_ENV, "")
    headers = {{"Authorization": f"Bearer {{token}}"}}
    resp = requests.get(f"{{BASE_URL}}/users/me", headers=headers)
    try:
        data = resp.json()
    except Exception:
        data = {{}}
    return {{"ok": bool(resp.ok), "data": data}}
'''
    action_code = ""
    for action in actions or []:
        action_code += f"""

def {action}(payload: dict) -> dict:
    \"\"\"Call Zoom API endpoint '{action}'.\"\"\"
    token = os.getenv(TOKEN_ENV, "")
    headers = {{"Authorization": f"Bearer {{token}}"}}
    resp = requests.post(f"{{BASE_URL}}/{action}", headers=headers, json=payload)
    try:
        return resp.json()
    except Exception:
        return {{}}
"""
    return (header + action_code).rstrip()

def _ticketing_template(service_type: str, base_url: str, token_env: str, actions: list[str]) -> str:
    """Generate a ServiceNow/Zendesk connector."""
    base = base_url or ""
    header = f'''"""
{service_type} Connector auto-generated by AIOps scaffolder.
"""
import os
import requests

BASE_URL = "{base}"
TOKEN_ENV = "{token_env}"

def health() -> dict:
    """Verify {service_type} connectivity by making a simple GET request."""
    token = os.getenv(TOKEN_ENV, "")
    headers = {{"Authorization": f"Bearer {{token}}"}}
    try:
        resp = requests.get(BASE_URL, headers=headers)
        ok = bool(resp.ok)
        data = resp.json() if hasattr(resp, "json") else {{}}
    except Exception:
        ok = False
        data = {{}}
    return {{"ok": ok, "data": data}}
'''
    action_code = ""
    for action in actions or []:
        action_code += f"""

def {action}(payload: dict) -> dict:
    \"\"\"Perform the '{action}' action on {service_type}.\"\"\"
    token = os.getenv(TOKEN_ENV, "")
    headers = {{"Authorization": f"Bearer {{token}}"}}
    resp = requests.post(f"{{BASE_URL}}/{action}", headers=headers, json=payload)
    try:
        return resp.json()
    except Exception:
        return {{}}
"""
    return (header + action_code).rstrip()

def _device_template(service_type: str, base_url: str, token_env: str, actions: list[str]) -> str:
    """Generate a Q-SYS or Extron device connector."""
    base = base_url or ""
    header = f'''"""
{service_type} Device Connector auto-generated by AIOps scaffolder.
"""
import os
import requests

BASE_URL = "{base}"
TOKEN_ENV = "{token_env}"

def health() -> dict:
    """Ping the device to verify connectivity."""
    try:
        resp = requests.get(f"{{BASE_URL}}/health")
        ok = bool(resp.ok)
        data = resp.json() if hasattr(resp, "json") else {{}}
    except Exception:
        ok = False
        data = {{}}
    return {{"ok": ok, "data": data}}
'''
    action_code = ""
    for action in actions or []:
        action_code += f"""

def {action}(payload: dict) -> dict:
    \"\"\"Perform the '{action}' action on {service_type}.\"\"\"
    resp = requests.post(f"{{BASE_URL}}/{action}", json=payload)
    try:
        return resp.json()
    except Exception:
        return {{}}
"""
    return (header + action_code).rstrip()

def _generic_template(service_type: str, base_url: str, token_env: str, actions: list[str]) -> str:
    """Generate a generic connector for unknown service types."""
    base = base_url or ""
    header = f'''"""
{service_type} Connector (generic) auto-generated by AIOps scaffolder.
"""
import os
import requests

BASE_URL = "{base}"
TOKEN_ENV = "{token_env}"

def health() -> dict:
    """Perform a basic health check by sending a GET request to the base URL."""
    token = os.getenv(TOKEN_ENV, "")
    try:
        resp = requests.get(BASE_URL, headers={{"Authorization": f"Bearer {{token}}"}})
        ok = bool(resp.ok)
        data = resp.json() if hasattr(resp, "json") else {{}}
    except Exception:
        ok = False
        data = {{}}
    return {{"ok": ok, "data": data}}
'''
    action_code = ""
    for action in actions or []:
        action_code += f"""

def {action}(payload: dict) -> dict:
    \"\"\"Invoke the '{action}' endpoint for the {service_type} connector.\"\"\"
    token = os.getenv(TOKEN_ENV, "")
    resp = requests.post(f"{{BASE_URL}}/{action}", headers={{"Authorization": f"Bearer {{token}}"}}, json=payload)
    try:
        return resp.json()
    except Exception:
        return {{}}
"""
    return (header + action_code).rstrip()
