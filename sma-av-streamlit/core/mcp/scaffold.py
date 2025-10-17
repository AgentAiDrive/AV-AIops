
from __future__ import annotations
import os, json

def scaffold(base_dir: str, tool_name: str):
    tools_dir = os.path.join(base_dir, "core", "mcp", "tools")
    os.makedirs(tools_dir, exist_ok=True)
    dest = os.path.join(tools_dir, tool_name)
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({
            "name": tool_name,
            "description": f"Scaffolded MCP tool {tool_name}",
            "endpoints": ["/health", "/action"]
        }, f, indent=2)
    with open(os.path.join(dest, "README.md"), "w", encoding="utf-8") as f:
        f.write(f"# {tool_name}\n\nThis is a scaffolded MCP tool placeholder.\n")
