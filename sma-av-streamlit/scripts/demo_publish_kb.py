import os, json, sys
from pathlib import Path
from core.agents.kb_publisher import KBPublisherAgent

# wire your LLM here (example only)
from core.llm.client import chat  # your existing function

def main(sop_path: str, kb_base_sys_id: str):
    sop = Path(sop_path).read_text(encoding="utf-8")
    agent = KBPublisherAgent(llm_chat_fn=chat)
    res = agent.run(
        sop_markdown=sop,
        kb_base_sys_id=kb_base_sys_id,
        category="Operations > AV",
        tags=["zoom","incident","touchpanel"],
        attachments=[],            # e.g., ["artifacts/diagram.png"]
        publish_if_allowed=False,
    )
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/demo_publish_kb.py <sop.md> <kb_base_sys_id>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
