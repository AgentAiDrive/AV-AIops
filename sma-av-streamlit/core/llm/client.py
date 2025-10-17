# core/llm/client.py
from __future__ import annotations
import os
from typing import Any, Dict, List, Literal, Tuple

__LLM_CLIENT_VERSION__ = "1.0.3-no-fallback"

try:
    import streamlit as st
except Exception:
    class _S: session_state = {}
    st = _S()  # type: ignore

from core.secrets import get_active_key  # reads st.secrets/env and respects selected provider

Provider = Literal["openai", "anthropic"]

_CLIENT: Any = None
_CLIENT_PROVIDER: Provider | None = None
_CLIENT_SRC: str | None = None  # where the key came from

def _build_client() -> Tuple[Any, Provider, str]:
    key, provider, source = get_active_key()  # (key|None, "openai"/"anthropic", "source string")
    if not key:
        raise RuntimeError(
            f"LLM key not found for provider '{provider}'. "
            f"Set Streamlit secrets or env. (sources tried: {source})"
        )

    if os.getenv("MOCK_LLM", "").strip().lower() in ("1","true","yes","on"):
        raise RuntimeError("MOCK_LLM is enabled; disable it to use a real provider.")

    if provider == "openai":
        try:
            from openai import OpenAI  # openai>=1.x
        except Exception as e:
            raise RuntimeError(f"OpenAI SDK not available: {e}")
        client = OpenAI(api_key=key)
        return client, "openai", source

    # provider == "anthropic"
    try:
        import anthropic  # anthropic>=0.20
    except Exception as e:
        raise RuntimeError(f"Anthropic SDK not available: {e}")
    client = anthropic.Anthropic(api_key=key)
    return client, "anthropic", source

def _ensure_client() -> Tuple[Any, Provider]:
    global _CLIENT, _CLIENT_PROVIDER, _CLIENT_SRC
    if _CLIENT is None:
        _CLIENT, _CLIENT_PROVIDER, _CLIENT_SRC = _build_client()
    return _CLIENT, _CLIENT_PROVIDER  # type: ignore

def refresh_client() -> None:
    """Call this if provider/keys change during the session."""
    global _CLIENT, _CLIENT_PROVIDER, _CLIENT_SRC
    _CLIENT = None
    _CLIENT_PROVIDER = None
    _CLIENT_SRC = None

def whoami() -> dict:
    """
    Returns runtime information about the active client.
    Will build the client if not yet built.
    """
    c, p = _ensure_client()
    return {
        "provider": p,
        "version": __LLM_CLIENT_VERSION__,
        "source": _CLIENT_SRC,
    }

def _oai_chat(client: Any, messages: List[Dict[str, str]], json_mode: bool) -> str:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    oai_msgs = [{"role": m["role"], "content": m["content"]} for m in messages if "content" in m]
    resp = client.chat.completions.create(
        model=model,
        messages=oai_msgs,
        temperature=0.2,
        response_format={"type": "json_object"} if json_mode else None,
    )
    out = resp.choices[0].message.content
    if isinstance(out, list):
        out = "".join([getattr(p, "text", "") or p.get("text", "") for p in out])
    return out or ""

def _anth_chat(client: Any, messages: List[Dict[str, str]], json_mode: bool) -> str:
    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")

    # Build Anthropic-compatible conversation
    system = ""
    turns = []
    for m in messages:
        role, content = m.get("role"), m.get("content", "")
        if role == "system":
            system = content
        elif role in ("user", "assistant"):
            turns.append({"role": role, "content": content})

    # If caller requested JSON, instruct via system message (no metadata hacks)
    if json_mode:
        extra_json_instr = (
            "\n\nYou must return ONLY a single valid JSON object. "
            "Do not include any prose or code fences."
        )
        system = (system or "") + extra_json_instr

    resp = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system or None,
        messages=turns,
        temperature=0.2,
        # DO NOT send arbitrary keys in metadata; Anthropic rejects unknown fields.
        # metadata={"user_id": "avops"}  # optional, if you want a user_id
    )

    # Collapse text blocks into a single string
    parts = []
    for blk in getattr(resp, "content", []):
        if getattr(blk, "type", "") == "text":
            parts.append(getattr(blk, "text", ""))
        elif isinstance(blk, dict) and blk.get("type") == "text":
            parts.append(blk.get("text", ""))
    return "".join(parts)

def chat(messages: List[Dict[str, str]], json_mode: bool = False) -> str:
    """
    Real provider only. No auto-fallback. Any failure raises.
    """
    client, provider = _ensure_client()
    if provider == "openai":
        return _oai_chat(client, messages, json_mode)
    else:
        return _anth_chat(client, messages, json_mode)
