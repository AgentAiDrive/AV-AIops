import re
import hashlib
from html import escape
from typing import Dict, Any
try:
    import bleach  # pip install bleach
except Exception:
    bleach = None

KB_SCHEMA = {
    "type": "object",
    "required": ["short_description", "html", "kb_base_sys_id"],
    "properties": {
        "short_description": {"type": "string", "minLength": 8, "maxLength": 160},
        "html": {"type": "string", "minLength": 32},
        "kb_base_sys_id": {"type": "string", "minLength": 32, "maxLength": 32},
        "category": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "valid_to": {"type": "string"},  # YYYY-MM-DD (optional)
    },
    "additionalProperties": False,
}

def sanitize_html(html: str) -> str:
    if bleach:
        return bleach.clean(
            html,
            tags=["p","ol","ul","li","strong","em","code","pre","h2","h3","h4","a","table","thead","tbody","tr","th","td","blockquote","br"],
            attributes={"a": ["href", "title", "target"]},
            strip=True,
        )
    # Fallback: escape everything if bleach not available
    return f"<pre>{escape(html)}</pre>"

def content_fingerprint(record: Dict[str, Any]) -> str:
    """Deterministic hash to avoid dupes (store it in a custom field if you add one)."""
    key = f"{record.get('short_description','')}|{record.get('html','')}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
