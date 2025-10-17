
from __future__ import annotations
import re
from sqlalchemy.orm import Session
from .service import save_recipe_yaml
from ..db.models import Agent, Recipe

def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return s or "recipe"

def attach_recipe_to_agent(db: Session, agent_name: str, recipe_name: str, yml: str):
    agent = db.query(Agent).filter(Agent.name==agent_name).first()
    if not agent:
        agent = Agent(name=agent_name, domain=agent_name.lower(), config_json={})
        db.add(agent); db.commit(); db.refresh(agent)
    fn = f"{_slug(recipe_name)}.yaml"
    save_recipe_yaml(fn, yml)
    recipe = db.query(Recipe).filter(Recipe.name==recipe_name).first()
    if not recipe:
        recipe = Recipe(name=recipe_name, yaml_path=fn)
        db.add(recipe); db.commit(); db.refresh(recipe)
    return agent, recipe
