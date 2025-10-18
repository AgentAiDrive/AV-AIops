"""Sample MCP connector for Extron device control."""
from __future__ import annotations

from typing import Dict


def set_input(device_id: str, input: int, output: int) -> Dict[str, int | str]:
    """Stub for switching inputs."""
    return {"device_id": device_id, "input": input, "output": output}


def trigger_macro(device_id: str, macro: str) -> Dict[str, str]:
    """Stub for macro invocation."""
    return {"device_id": device_id, "macro": macro, "status": "triggered"}
