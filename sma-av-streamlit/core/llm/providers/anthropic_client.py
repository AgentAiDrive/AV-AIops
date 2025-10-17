
from __future__ import annotations
from typing import List, Dict

def chat_claude(api_key: str, messages: List[Dict], model: str = "claude-3-haiku-20240307") -> str:
    last = messages[-1]["content"] if messages else ""
    return f"(anthropic simulated {model}) {last[:200]}"
