"""Sample MCP connector for incident ticketing platforms."""
from __future__ import annotations

from typing import Dict


def create_ticket(title: str, description: str, priority: str, service: str) -> Dict[str, str]:
    """Stub for creating an incident ticket."""
    return {
        "id": "INC-12345",
        "title": title,
        "description": description,
        "priority": priority,
        "service": service,
        "status": "new",
    }


def update_state(ticket_id: str, state: str) -> Dict[str, str]:
    """Stub for transitioning ticket state."""
    return {"id": ticket_id, "status": state}
