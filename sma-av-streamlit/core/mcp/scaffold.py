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

# (templates unchanged from your version)
