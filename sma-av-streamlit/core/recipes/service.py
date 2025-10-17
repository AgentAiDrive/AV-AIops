
from __future__ import annotations
import os, yaml
from typing import Dict, Any, List, Tuple
from .validator import validate_yaml_text

RECIPES_DIR = os.path.join(os.getcwd(), "recipes")

def list_recipe_files() -> List[str]:
    if not os.path.isdir(RECIPES_DIR):
        return []
    return sorted([f for f in os.listdir(RECIPES_DIR) if f.endswith(".yaml")])

def load_recipe_dict(filename: str) -> Dict[str, Any]:
    path = os.path.join(RECIPES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def save_recipe_yaml(filename: str, yaml_text: str) -> str:
    os.makedirs(RECIPES_DIR, exist_ok=True)
    path = os.path.join(RECIPES_DIR, filename)
    ok, msg = validate_yaml_text(yaml_text)
    if not ok:
        raise ValueError(msg)
    with open(path, "w", encoding="utf-8") as f:
        f.write(yaml_text)
    return path
