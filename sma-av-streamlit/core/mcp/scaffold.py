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
) -> None:
    """Generate a new MCP tool with a manifest and example implementation.

    The scaffold writes a manifest file, README, and a Python module implementing
    health and action endpoints.  Supported service types include Slack, Zoom,
    ServiceNow/Zendesk, Q-SYS/Extron, and a generic fallback.  The scopes_json
    argument should contain a JSON object with an "actions" array to specify
    which endpoints to create.  Tokens are pulled from environment variables or
    Streamlit secrets as specified by token_env.

    Args:
        base_dir: project root (usually os.getcwd())
        tool_name: slug for the tool (e.g. "slack")
        service_type: human-friendly type (e.g. Slack, Zoom)
        base_url: default API base URL for the service
        token_env: name of the environment variable that holds the API token
        scopes_json: JSON string describing supported actions
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

    # Construct the manifest
    manifest = {
        "name": tool_name,
        "type": service_type,
        "description": f"Connector for {service_type}",
        "endpoints": ["/health"] + [f"/{action}" for action in scopes.get("actions", [])],
        "token_env": token_env,
        "base_url": base_url,
        "actions": scopes.get("actions", []),
    }
    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Write README with usage instructions
    readme_text = (
        f"# {service_type} Connector\n\n"
        f"This connector integrates the application with the {service_type} API.\n\n"
        f"Set your secret in `.streamlit/secrets.toml` or as an environment variable named {token_env}.\n"
        "The `health` endpoint calls a basic API method to verify connectivity,\n"
        "and each action endpoint implements one automation action.\n"
    )
    with open(os.path.join(dest, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_text)

    # Choose a template based on service_type
    impl_path = os.path.join(dest, f"{tool_name}.py")
    service_key = service_type.lower()
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


# Template functions below build example connectors for each service.

def _slack_template(base_url: str, token_env: str, actions: list[str]) -> str:
    """Generate a Slack connector module."""
    if not actions:
        actions = ["send_message"]
    return textwrap.dedent(
        f"""
        import os
        import requests
        from flask import Flask, request, jsonify

        app = Flask(__name__)

        BASE_URL = "{(base_url or 'https://slack.com/api').rstrip('/')}"
        TOKEN = os.getenv("{token_env}")

        def slack_api(method: str, payload: dict | None = None):
            if not TOKEN:
                raise RuntimeError("Slack token missing; set {token_env} in secrets or env.")
            url = f"{{BASE_URL}}/{{method}}"
            headers = {"Authorization": f"Bearer {{TOKEN}}", "Content-Type": "application/json"}
            resp = requests.post(url, headers=headers, json=payload or {{}})
            return resp.json()

        @app.route("/health", methods=["GET"])
        def health():
            try:
                result = slack_api("auth.test")
                return jsonify({{"ok": bool(result.get("ok")), "user": result.get("user")}})
            except Exception as exc:
                return jsonify({{"ok": False, "error": str(exc)}}), 500

        @app.route("/send_message", methods=["POST"])
        def send_message():
            data = request.get_json(silent=True) or {{}}
            channel = data.get("channel")
            text = data.get("text")
            if not channel or not text:
                return jsonify({{"error": "Missing channel or text"}}), 400
            res = slack_api("chat.postMessage", {{"channel": channel, "text": text}})
            return jsonify(res)

        # Additional actions can be implemented here.

        if __name__ == "__main__":
            # Start the connector on a default port; override via PORT env.
            app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8901)))
        """
    )


def _zoom_template(base_url: str, token_env: str, actions: list[str]) -> str:
    """Generate a Zoom connector module."""
    if not actions:
        actions = ["create_meeting"]
    return textwrap.dedent(
        f"""
        import os
        import requests
        from flask import Flask, request, jsonify

        app = Flask(__name__)

        BASE_URL = "{(base_url or 'https://api.zoom.us/v2').rstrip('/')}"
        TOKEN = os.getenv("{token_env}")  # expects JWT or OAuth access token

        def zoom_api(path: str, method: str = "GET", payload: dict | None = None):
            if not TOKEN:
                raise RuntimeError("Zoom token missing; set {token_env} in secrets or env.")
            url = f"{{BASE_URL}}/{{path.lstrip('/')}}"
            headers = {"Authorization": f"Bearer {{TOKEN}}" }
            if method.upper() == "GET":
                resp = requests.get(url, headers=headers, params=payload or {{}})
            else:
                resp = requests.post(url, headers={{**headers, "Content-Type": "application/json"}}, json=payload or {{}})
            return resp.json()

        @app.route("/health", methods=["GET"])
        def health():
            try:
                me = zoom_api("users/me")
                return jsonify({{"ok": not bool(me.get("code")), "user": me.get("id")}})
            except Exception as exc:
                return jsonify({{"ok": False, "error": str(exc)}}), 500

        @app.route("/create_meeting", methods=["POST"])
        def create_meeting():
            data = request.get_json(silent=True) or {{}}
            user_id = data.get("user_id") or "me"
            topic = data.get("topic") or "Auto-generated meeting"
            payload = {{
                "topic": topic,
                "type": 1,
                "settings": {{"join_before_host": True}},
            }}
            res = zoom_api(f"users/{{user_id}}/meetings", method="POST", payload=payload)
            return jsonify(res)

        if __name__ == "__main__":
            app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8902)))
        """
    )


def _ticketing_template(service_type: str, base_url: str, token_env: str, actions: list[str]) -> str:
    """Generate a ServiceNow/Zendesk connector module."""
    if not actions:
        actions = ["create_ticket"]
    return textwrap.dedent(
        f"""
        import os
        import requests
        from flask import Flask, request, jsonify

        app = Flask(__name__)

        BASE_URL = "{(base_url or '').rstrip('/')}"
        TOKEN = os.getenv("{token_env}")

        def api(path: str, method: str = "GET", payload: dict | None = None):
            if not TOKEN:
                raise RuntimeError("{service_type} token missing; set {token_env} in secrets or env.")
            url = f"{{BASE_URL}}/{{path.lstrip('/')}}"
            headers = {"Authorization": f"Bearer {{TOKEN}}", "Accept": "application/json"}
            if method.upper() == "GET":
                resp = requests.get(url, headers=headers, params=payload or {{}})
            else:
                resp = requests.post(url, headers={{**headers, "Content-Type": "application/json"}}, json=payload or {{}})
            return resp.json()

        @app.route("/health", methods=["GET"])
        def health():
            try:
                # check API root or user profile
                check = api("/api/now/table/sys_user?sysparm_limit=1")
                ok = bool(check.get("result"))
                return jsonify({{"ok": ok}})
            except Exception as exc:
                return jsonify({{"ok": False, "error": str(exc)}}), 500

        @app.route("/create_ticket", methods=["POST"])
        def create_ticket():
            data = request.get_json(silent=True) or {{}}
            short_desc = data.get("short_description") or "Auto-generated ticket"
            description = data.get("description") or "No details provided."
            payload = {{"short_description": short_desc, "description": description}}
            res = api("/api/now/table/incident", method="POST", payload=payload)
            return jsonify(res)

        if __name__ == "__main__":
            app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8903)))
        """
    )


def _device_template(service_type: str, base_url: str, token_env: str, actions: list[str]) -> str:
    """Generate a device controller connector (Q-SYS/Extron)."""
    if not actions:
        actions = ["power_on", "power_off"]
    return textwrap.dedent(
        f"""
        import os
        import requests
        from flask import Flask, request, jsonify

        app = Flask(__name__)

        BASE_URL = "{(base_url or '').rstrip('/')}"
        TOKEN = os.getenv("{token_env}")

        def send_command(command: str):
            if not TOKEN:
                raise RuntimeError("Device controller token missing; set {token_env} in secrets or env.")
            url = f"{{BASE_URL}}/commands/{{command}}"
            headers = {"Authorization": f"Bearer {{TOKEN}}"}
            resp = requests.post(url, headers=headers)
            return resp.status_code, resp.text

        @app.route("/health", methods=["GET"])
        def health():
            try:
                status, _ = send_command("status")
                return jsonify({{"ok": status == 200}})
            except Exception as exc:
                return jsonify({{"ok": False, "error": str(exc)}}), 500

        @app.route("/power_on", methods=["POST"])
        def power_on():
            status, text = send_command("power_on")
            return (text, status)

        @app.route("/power_off", methods=["POST"])
        def power_off():
            status, text = send_command("power_off")
            return (text, status)

        if __name__ == "__main__":
            app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8904)))
        """
    )


def _generic_template(service_type: str, base_url: str, token_env: str, actions: list[str]) -> str:
    """Generate a generic connector skeleton."""
    return textwrap.dedent(
        f"""
        # Generic connector template for {service_type}
        # Fill in API paths and actions manually.
        import os
        import requests
        from flask import Flask, request, jsonify

        app = Flask(__name__)

        BASE_URL = "{(base_url or '').rstrip('/')}"
        TOKEN = os.getenv("{token_env}")

        @app.route("/health", methods=["GET"])
        def health():
            # Replace with a real health check
            return jsonify({{"ok": True, "message": "Health check not implemented"}})

        # Define action endpoints below using the actions list: {actions}

        if __name__ == "__main__":
            app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8900)))
        """
    )
