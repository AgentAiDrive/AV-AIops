from __future__ import annotations
from typing import Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from uuid import uuid4

from ..db.models import WorkflowDef
from .engine import execute_recipe_run
from core.runstore_factory import make_runstore  # shared store

def list_workflows(db: Session):
    return db.query(WorkflowDef).order_by(WorkflowDef.id.asc()).all()

def _workflow_name_exists(db: Session, name: str, *, exclude_id: Optional[int] = None) -> bool:
    q = db.query(WorkflowDef.id).filter(func.lower(WorkflowDef.name) == name.lower())
    if exclude_id is not None:
        q = q.filter(WorkflowDef.id != exclude_id)
    return q.first() is not None

def create_workflow(db: Session, name: str, agent_id: int, recipe_id: int,
                    trigger_type: str = "manual", trigger_value: Optional[int] = None):
    if _workflow_name_exists(db, name):
        raise ValueError(f"Workflow '{name}' already exists.")
    wf = WorkflowDef(
        name=name,
        agent_id=agent_id,
        recipe_id=recipe_id,
        trigger_type=trigger_type,
        trigger_value=trigger_value,
        status="yellow",
        enabled=1,
    )
    if trigger_type == "interval" and trigger_value:
        wf.next_run_at = datetime.utcnow() + timedelta(minutes=trigger_value)
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf

def update_workflow(db: Session, wf_id: int, **kwargs):
    wf = db.query(WorkflowDef).filter(WorkflowDef.id == wf_id).first()
    if not wf:
        return None
    if "name" in kwargs and kwargs["name"] is not None:
        new_name = kwargs["name"].strip()
        if not new_name:
            raise ValueError("Workflow name cannot be empty.")
        if new_name.lower() != wf.name.lower() and _workflow_name_exists(db, new_name, exclude_id=wf_id):
            raise ValueError(f"Workflow '{new_name}' already exists.")
        kwargs["name"] = new_name
    recipe_changed = False
    for k, v in kwargs.items():
        if hasattr(wf, k) and v is not None:
            if k == "recipe_id" and v != getattr(wf, k):
                recipe_changed = True
            setattr(wf, k, v)
        if k == "trigger_type" and v == "manual":
            wf.next_run_at = None
        if k == "trigger_type" and v == "interval" and kwargs.get("trigger_value"):
            wf.next_run_at = datetime.utcnow() + timedelta(minutes=int(kwargs["trigger_value"]))
    if recipe_changed:
        wf.last_run_at = None
        wf.next_run_at = None
        wf.status = "yellow"
    db.commit()
    db.refresh(wf)
    return wf

def delete_workflow(db: Session, wf_id: int) -> bool:
    wf = db.query(WorkflowDef).filter(WorkflowDef.id == wf_id).first()
    if not wf:
        return False
    db.delete(wf)
    db.commit()
    return True

def compute_status(wf: WorkflowDef) -> str:
    if not wf.last_run_at:
        return "yellow"
    delta = datetime.utcnow() - wf.last_run_at
    if delta.total_seconds() <= 24 * 3600:
        return "green"
    if delta.total_seconds() <= 7 * 24 * 3600:
        return "yellow"
    return "red"

def run_now(db: Session, wf_id: int):
    """
    Trigger a workflow immediately and record it in RunStore.
    The RunStore entry will have status='running' during execution and
    update to 'success' or 'failed' on completion.
    """
    wf = db.query(WorkflowDef).filter(WorkflowDef.id == wf_id).first()
    if not wf:
        return None

    store = make_runstore()

    # Use workflow_run context manager to record start and finish in RunStore
    # workflow_id is stored as a string; using wf.id ensures uniqueness.
    with store.workflow_run(
        workflow_id=str(wf.id),
        name=wf.name,
        agent_id=wf.agent_id,
        recipe_id=wf.recipe_id,
        trigger="manual",
        meta={"workflow_name": wf.name},
    ) as rec:
        # Execute the recipe (primary DB run)
        run = execute_recipe_run(db, agent_id=wf.agent_id, recipe_id=wf.recipe_id)
        # Optionally log a step summary in RunStore
        rec.step(
            phase="act",
            message=f"Executed recipe {run.recipe_id}",
            payload=None,
            result={"status": "completed"},
        )

    # Update workflow timestamps/status after run
    wf.last_run_at = datetime.utcnow()
    wf.status = compute_status(wf)
    if wf.trigger_type == "interval" and wf.trigger_value:
        wf.next_run_at = datetime.utcnow() + timedelta(minutes=wf.trigger_value)
    db.commit()
    db.refresh(wf)
    return run

def tick(db: Session) -> int:
    now = datetime.utcnow()
    due = (
        db.query(WorkflowDef)
        .filter(
            WorkflowDef.enabled == 1,
            WorkflowDef.trigger_type == "interval",
            WorkflowDef.next_run_at != None,  # noqa: E711
            WorkflowDef.next_run_at <= now,
        )
        .all()
    )
    count = 0
    for wf in due:
        run_now(db, wf.id)
        count += 1
    return count
