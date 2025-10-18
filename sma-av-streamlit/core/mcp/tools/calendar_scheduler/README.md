# Calendar Scheduler MCP Connector

This sample connector demonstrates how to expose meeting scheduling actions as MCP endpoints.

* `create_event` — provision a meeting with a room, technician, and attendees.
* `reschedule_event` — move an existing appointment.
* `cancel_event` — mark a meeting as cancelled and notify participants.

Replace the stub functions in `connector.py` with calls to your preferred calendar provider (Exchange, Google Calendar, ServiceNow calendar, etc.).
