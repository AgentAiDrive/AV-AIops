# MCP Tool Samples

The `core/mcp/tools` directory now includes sample connectors for common AV/IT workflows:

| Connector | Purpose |
|-----------|---------|
| `calendar_scheduler` | Schedule rooms, technicians, and AV resources. |
| `incident_ticketing` | File and update incidents across ITSM platforms. |
| `qsys_control` | Interact with Q-SYS processors for audio/video routing. |
| `extron_control` | Trigger macros and switch inputs on Extron hardware. |

Each folder provides a `manifest.json`, implementation stub in `connector.py`, and documentation in `README.md`. Use the scaffolder on the **🧰 MCP Tools** page to clone these examples for new tools.
