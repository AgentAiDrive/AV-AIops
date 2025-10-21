import json
from typing import List, Optional, Dict, Any
from core.tools import servicenow as sn
from core.guards.kb_article_schema import KB_SCHEMA, sanitize_html, content_fingerprint

try:
    from jsonschema import validate, ValidationError  # pip install jsonschema
except Exception:
    validate = None
    ValidationError = Exception

class KBPublisherAgent:
    """
    Intake → Plan → Act → Verify
    - intake: collect SOP markdown + metadata
    - plan: ask LLM to produce fields for KB_SCHEMA
    - act: create KB + attachments
    - verify: fetch & validate persisted state
    """

    def __init__(self, llm_chat_fn):
        self.chat = llm_chat_fn  # signature: chat(system, messages) -> str/json

    def _plan_from_sop(self, sop_markdown: str, kb_base_sys_id: str, category: Optional[str], tags: List[str]) -> Dict[str, Any]:
        system = (
            "You extract structured fields for a ServiceNow KB article. "
            "Return ONLY JSON matching this schema: "
            + json.dumps(KB_SCHEMA)
        )
        user = f"""SOP (Markdown):
