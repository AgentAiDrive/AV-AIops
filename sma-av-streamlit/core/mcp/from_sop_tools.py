
from __future__ import annotations
import os
from .scaffold import scaffold

HINTS = {
    "slack": ["slack", "channel", "dm"],
    "zoom": ["zoom", "webinar", "room", "meeting"],
    "servicenow": ["servicenow", "incident", "ticket"],
    "teams": ["microsoft teams", "teams"],
    "webex": ["webex"],
}

def ensure_tools_for_sop(base_dir: str, sop_text: str):
    low = sop_text.lower()
    detected = set()
    for tool, keys in HINTS.items():
        if any(k in low for k in keys):
            detected.add(tool)
    created = []
    for t in detected:
        path = os.path.join(base_dir, "core", "mcp", "tools", t)
        if not os.path.isdir(path):
            scaffold(base_dir, t); created.append(t)
    return sorted(list(detected)), created
