
from __future__ import annotations
import yaml
from typing import Tuple

REQUIRED_KEYS = ["name","description","intake","plan","act","verify"]

def validate_yaml_text(text: str) -> tuple[bool, str]:
    try:
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            return False, "YAML root must be a mapping"
        for k in REQUIRED_KEYS:
            if k not in data:
                return False, f"Missing key: {k}"
        return True, "ok"
    except Exception as e:
        return False, f"Invalid YAML: {e}"
