"""Sample MCP connector for Q-SYS control surfaces."""
from __future__ import annotations

from typing import Dict


def set_gain(device_id: str, channel: str, db: float) -> Dict[str, str]:
    """Stub gain adjustment."""
    return {"device_id": device_id, "channel": channel, "gain_db": db}


def recall_snapshot(snapshot: str) -> Dict[str, str]:
    """Stub snapshot recall."""
    return {"snapshot": snapshot, "status": "recalled"}
