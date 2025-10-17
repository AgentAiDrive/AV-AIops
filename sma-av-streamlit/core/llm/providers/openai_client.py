
from __future__ import annotations
from typing import List, Dict

def chat_openai(api_key: str, messages: List[Dict], model: str = "gpt-4o-mini") -> str:
    # Minimal stub: avoid network in default demo. Replace with real API call if desired.
    last = messages[-1]["content"] if messages else ""
    return f"(openai simulated {model}) {last[:200]}"
