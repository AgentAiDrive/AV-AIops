# core/secrets.py
from __future__ import annotations
import os
from typing import Optional, Tuple

try:
    import streamlit as st
except Exception:  # runtime without Streamlit (tests)
    class _Stub:
        secrets = {}
        session_state = {}
    st = _Stub()  # type: ignore

def _from_st_secrets_flat(key: str) -> Optional[str]:
    try:
        return st.secrets.get(key)  # type: ignore[attr-defined]
    except Exception:
        return None

def _from_st_secrets_nested(section: str, key: str) -> Optional[str]:
    try:
        sec = st.secrets.get(section)  # type: ignore[attr-defined]
        if isinstance(sec, dict):
            val = sec.get(key)
            return val
    except Exception:
        pass
    return None

def _clean(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = str(s).strip()
    return s if s else None

def get_openai_key() -> Tuple[Optional[str], str]:
    # Try common patterns in order
    for source, val in (
        ("st.secrets[openai].api_key", _from_st_secrets_nested("openai", "api_key")),
        ("st.secrets[OPENAI_API_KEY]", _from_st_secrets_flat("OPENAI_API_KEY")),
        ("env:OPENAI_API_KEY", os.getenv("OPENAI_API_KEY")),
        ("env:OPENAI_KEY", os.getenv("OPENAI_KEY")),
    ):
        v = _clean(val)
        if v:
            return v, source
    return None, "missing"

def get_anthropic_key() -> Tuple[Optional[str], str]:
    for source, val in (
        ("st.secrets[anthropic].api_key", _from_st_secrets_nested("anthropic", "api_key")),
        ("st.secrets[ANTHROPIC_API_KEY]", _from_st_secrets_flat("ANTHROPIC_API_KEY")),
        ("env:ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY")),
        ("env:CLAUDE_API_KEY", os.getenv("CLAUDE_API_KEY")),
    ):
        v = _clean(val)
        if v:
            return v, source
    return None, "missing"

def is_mock_enabled() -> bool:
    # Only explicit toggle enables mock. No silent fallback.
    v = st.session_state.get("mock_mcp", False)  # type: ignore[attr-defined]
    # Optional env override for CI
    env_v = os.getenv("MOCK_MCP")
    if env_v is not None:
        env_v = env_v.strip().lower()
        if env_v in ("1", "true", "yes", "on"):
            return True
        if env_v in ("0", "false", "no", "off"):
            return False
    return bool(v)

def pick_active_provider() -> str:
    p = (getattr(st, "session_state", {}).get("llm_provider") or "OpenAI").lower()  # type: ignore[attr-defined]
    return "anthropic" if p == "anthropic" else "openai"

def get_active_key() -> Tuple[Optional[str], str, str]:
    provider = pick_active_provider()
    if provider == "anthropic":
        k, src = get_anthropic_key()
        return k, "anthropic", src
    k, src = get_openai_key()
    return k, "openai", src
