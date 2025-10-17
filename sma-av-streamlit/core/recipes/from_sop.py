
from __future__ import annotations
import re, yaml
from typing import Tuple
from .validator import validate_yaml_text

def _heuristic_yaml(sop: str, name_hint: str) -> str:
    lines = [l.strip("-• ").strip() for l in sop.splitlines() if l.strip()]
    intake = [{"gather": l} for l in lines[:2]] or [{"gather":"context"}]
    plan = [{"step": l} for l in lines[2:5]] or [{"step":"Plan action"}]
    act = [{"action": l} for l in lines[5:8]] or [{"action":"Execute action"}]
    verify = [{"check": l} for l in lines[8:10]] or [{"check":"Verify outcome"}]
    data = {"name": name_hint, "description": (sop[:140] if sop else "Generated"), "intake": intake, "plan": plan, "act": act, "verify": verify}
    return yaml.safe_dump(data, sort_keys=False)

def sop_to_recipe_yaml(sop: str, name_hint: str = "Generated Recipe") -> Tuple[bool, str]:
    # LLM attempt skipped in offline demo; plug in provider calls if needed.
    yml = _heuristic_yaml(sop, name_hint)
    ok, _ = validate_yaml_text(yml)
    return True, yml
