# OpenAI MCP Agent Recipe Pack + Responses API (Structured Outputs)

This pack includes:
- A **shared prelude** for consistent system/developer priming.
- Five **few-shot MCP recipes** you can drop into the OpenAI Responses API.
- A minimal **Node.js snippet** wiring **remote MCP servers** and **Structured Outputs** with `parallel_tool_calls:false`.

> These files are **copy-paste ready** and align with the static Wizard + local MCP servers found under `mcp-tools/*`.

## Files

- `packages/recipes/openai-mcp/shared_prelude.jsonc`
- `packages/recipes/openai-mcp/AV.Events.CreatePackage.jsonc`
- `packages/recipes/openai-mcp/AV.Support.Triage.jsonc`
- `packages/recipes/openai-mcp/AV.Ops.RemoteRecover.jsonc`
- `packages/recipes/openai-mcp/AV.Builds.ZoomRoom.Provision.jsonc`
- `packages/recipes/openai-mcp/AV.Reporting.WeeklyOpsDigest.jsonc`
- `examples/openai/responses_mcp_strict.js`
- `examples/openai/schemas/EventAutomation.schema.json`

See inline comments and adapt server URLs to point at your MCP endpoints (local or deployed).
