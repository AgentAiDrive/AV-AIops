# core/llm/client.py
from __future__ import annotations
import os
from typing import Any, Dict, List, Literal, Tuple

try:
    import streamlit as st
except Exception:
    class _S: session_state = {}
    st = _S()  # type: ignore

from core.secrets import get_active_key  # uses st.secrets / env safely

Provider = Literal["openai", "anthropic"]

_CLIENT: Any = None
_CLIENT_PROVIDER: Provider | None = None

def _build_client() -> Tuple[Any, Provider]:
    key, provider, source = get_active_key()  # (key|None, "openai"/"anthropic", "source string")
    if not key:
        raise RuntimeError(
            f"LLM key not found for provider '{provider}'. "
            f"Check Streamlit secrets or env. (source tried: {source})"
        )

    if os.getenv("MOCK_LLM", "").strip().lower() in ("1", "true", "yes", "on"):
        raise RuntimeError("MOCK_LLM is enabled; disable it to use real provider.")

    if provider == "openai":
        try:
            from openai import OpenAI  # requires openai>=1.x
        except Exception as e:
            raise RuntimeError(f"OpenAI SDK not available: {e}")
        client = OpenAI(api_key=key)
        return client, "openai"

    else:
        try:
            import anthropic  # requires anthropic>=0.20
        except Exception as e:
            raise RuntimeError(f"Anthropic SDK not available: {e}")
        client = anthropic.Anthropic(api_key=key)
        return client, "anthropic"

def _ensure_client() -> Tuple[Any, Provider]:
    global _CLIENT, _CLIENT_PROVIDER
    if _CLIENT is None:
        _CLIENT, _CLIENT_PROVIDER = _build_client()
    return _CLIENT, _CLIENT_PROVIDER  # type: ignore

def refresh_client() -> None:
    """Call this if provider/keys change during the session."""
    global _CLIENT, _CLIENT_PROVIDER
    _CLIENT = None
    _CLIENT_PROVIDER = None

def _oai_chat(client: Any, messages: List[Dict[str, str]], json_mode: bool) -> str:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    # Normalize messages to OpenAI format
    oai_msgs = [{"role": m["role"], "content": m["content"]} for m in messages if "content" in m]
    resp = client.chat.completions.create(
        model=model,
        messages=oai_msgs,
        response_format={"type": "json_object"} if json_mode else None,
    )
    out = resp.choices[0].message.content
    if isinstance(out, list):
        out = "".join([getattr(p, "text", "") or p.get("text", "") for p in out])  # safety
    return out or ""

def _anth_chat(client: Any, messages: List[Dict[str, str]], json_mode: bool) -> str:
    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
    system = ""
    turns = []
    for m in messages:
        role, content = m.get("role"), m.get("content", "")
        if role == "system":
            system = content
        elif role in ("user", "assistant"):
            turns.append({"role": role, "content": content})
    resp = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system or None,
        messages=turns,
        metadata={"json_mode": json_mode},
    )
    parts = []
    for blk in getattr(resp, "content", []):
        if getattr(blk, "type", "") == "text":
            parts.append(getattr(blk, "text", ""))
        elif isinstance(blk, dict) and blk.get("type") == "text":
            parts.append(blk.get("text", ""))
    return "".join(parts)

def chat(messages: List[Dict[str, str]], json_mode: bool = False) -> str:
    """
    Real provider only. No auto-mock. Any failure raises.
    UI should catch and display the error.
    """
    client, provider = _ensure_client()
    if provider == "openai":
        return _oai_chat(client, messages, json_mode)
    else:
        return _anth_chat(client, messages, json_mode)
