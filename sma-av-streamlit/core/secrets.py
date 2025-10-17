# core/secrets.py
from __future__ import annotations
import os
from typing import Optional, Tuple

try:
    import streamlit as st
except Exception:
    class _Stub:
        secrets = {}
        session_state = {}
    st = _Stub()  # type: ignore

# ---------- helpers ----------

def _clean(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = str(s).strip()
    return s if s else None

def _from_session(key: str) -> Optional[str]:
    try:
        v = st.session_state.get(key)  # type: ignore[attr-defined]
        return _clean(v)
    except Exception:
        return None

def _from_st_secrets_flat(key: str) -> Optional[str]:
    try:
        return _clean(st.secrets.get(key))  # type: ignore[attr-defined]
    except Exception:
        return None

def _from_st_secrets_nested(section: str, key: str) -> Optional[str]:
    try:
        sec = st.secrets.get(section)  # type: ignore[attr-defined]
        if isinstance(sec, dict):
            return _clean(sec.get(key))
    except Exception:
        pass
    return None

def _from_env(*keys: str) -> Optional[str]:
    for k in keys:
        v = _clean(os.getenv(k))
        if v:
            return v
    return None

# ---------- public API ----------

def get_openai_key() -> Tuple[Optional[str], str]:
    """
    Returns (key, source_string) with precedence:
    session override -> st.secrets nested -> st.secrets flat -> env
    """
    for source, val in (
        ("session[OPENAI_API_KEY]", _from_session("OPENAI_API_KEY")),
        ("st.secrets[openai].api_key", _from_st_secrets_nested("openai", "api_key")),
        ("st.secrets[OPENAI_API_KEY]", _from_st_secrets_flat("OPENAI_API_KEY")),
        ("env:OPENAI_API_KEY/OPENAI_KEY", _from_env("OPENAI_API_KEY", "OPENAI_KEY")),
    ):
        if val:
            return val, source
    return None, "missing"

def get_anthropic_key() -> Tuple[Optional[str], str]:
    """
    Returns (key, source_string) with precedence:
    session override -> st.secrets nested -> st.secrets flat -> env
    """
    for source, val in (
        ("session[ANTHROPIC_API_KEY]", _from_session("ANTHROPIC_API_KEY")),
        ("st.secrets[anthropic].api_key", _from_st_secrets_nested("anthropic", "api_key")),
        ("st.secrets[ANTHROPIC_API_KEY]", _from_st_secrets_flat("ANTHROPIC_API_KEY")),
        ("env:ANTHROPIC_API_KEY/CLAUDE_API_KEY", _from_env("ANTHROPIC_API_KEY", "CLAUDE_API_KEY")),
    ):
        if val:
            return val, source
    return None, "missing"

def is_mock_enabled() -> bool:
    # explicit session toggle wins; env can override for CI if set
    v = bool(getattr(st, "session_state", {}).get("mock_mcp", False))  # type: ignore[attr-defined]
    env_v = os.getenv("MOCK_MCP")
    if env_v is not None:
        ev = env_v.strip().lower()
        if ev in ("1", "true", "yes", "on"):
            return True
        if ev in ("0", "false", "no", "off"):
            return False
    return v

def pick_active_provider() -> str:
    # radio stores "OpenAI" | "Anthropic"; default OpenAI
    p = (getattr(st, "session_state", {}).get("llm_provider") or "OpenAI")  # type: ignore[attr-defined]
    return "anthropic" if str(p).lower() == "anthropic" else "openai"

def get_active_key() -> Tuple[Optional[str], str, str]:
    """
    Returns (key, provider, source_string).
    provider = "openai" | "anthropic"
    """
    provider = pick_active_provider()
    if provider == "anthropic":
        k, src = get_anthropic_key()
        return k, "anthropic", src
    k, src = get_openai_key()
    return k, "openai", src
