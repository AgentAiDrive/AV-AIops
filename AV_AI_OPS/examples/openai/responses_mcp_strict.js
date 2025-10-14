// examples/openai/responses_mcp_strict.js
// Minimal OpenAI Responses API + remote MCP servers + strict Structured Outputs
import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const tools = [
  { type: "mcp", server_label: "servicenow", server_url: "http://localhost:8405" },
  { type: "mcp", server_label: "zoom",       server_url: "http://localhost:8402" },
  { type: "mcp", server_label: "calendar",   server_url: "http://localhost:8410" } // example placeholder
];

const response_format = {
  type: "json_schema",
  json_schema: {
    name: "EventAutomation",
    schema: (await import("./schemas/EventAutomation.schema.json", { assert: { type: "json" }})).default,
    strict: true
  }
};

const input = [
  { role: "system",    content: "You are AV-AI-Ops. Prefer MCP tools. Be concise." },
  { role: "developer", content: "Create an AV event; return EventAutomation JSON only." },
  { role: "user",      content: "Create all_hands 'Q4 All-Hands' on 2025-11-05 10:00–11:00 PST at HQ1; platform zoom; registration yes; options: Q&A Moderation, RTMP Primary; POC Jane <jane@ex.com>." }
];

const res = await client.responses.create({
  model: "gpt-4o-2024-08-06",
  input,
  tools,
  parallel_tool_calls: false,
  response_format
});

console.log(res.output_text || JSON.stringify(res.output, null, 2));
