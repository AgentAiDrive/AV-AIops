"""Sample MCP connector for calendar scheduling systems."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List


def create_event(title: str, room: str, start: datetime, end: datetime, participants: List[str]) -> Dict[str, str]:
    """Stub implementation that would call Exchange/Google/Outlook APIs."""
    return {
        "status": "scheduled",
        "title": title,
        "room": room,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "participants": participants,
    }


def cancel_event(event_id: str) -> Dict[str, str]:
    """Stub cancellation handler."""
    return {"status": "cancelled", "event_id": event_id}
