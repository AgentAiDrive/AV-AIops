
from __future__ import annotations
from typing import Iterator, Dict, Any
from sqlalchemy.orm import Session
from ..db.models import Agent, Recipe, Run
from ..recipes.service import load_recipe_dict
from ..utils.evidence import attach_json

def run_workflow_phases(recipe: Dict[str, Any]) -> Iterator[tuple[str, str]]:
    for phase in ["intake", "plan", "act", "verify"]:
        steps = recipe.get(phase, []) or []
        yield phase, f"{phase} steps: {len(steps)}"

def execute_recipe_run(db: Session, agent_id: int, recipe_id: int) -> Run:
    agent = db.query(Agent).filter(Agent.id==agent_id).first()
    recipe = db.query(Recipe).filter(Recipe.id==recipe_id).first()
    run = Run(agent_id=agent_id, recipe_id=recipe_id, status="running")
    db.add(run); db.commit(); db.refresh(run)
    recipe_dict = load_recipe_dict(recipe.yaml_path)
    for phase, message in run_workflow_phases(recipe_dict):
        attach_json(db, run_id=run.id, payload={"phase": phase, "message": f"{agent.name}: {message}"})
    run.status = "completed"; db.commit(); db.refresh(run)
    return run
