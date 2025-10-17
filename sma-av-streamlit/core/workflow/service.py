
from __future__ import annotations
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..db.models import WorkflowDef
from .engine import execute_recipe_run

def list_workflows(db: Session):
    return db.query(WorkflowDef).order_by(WorkflowDef.id.asc()).all()

def create_workflow(db: Session, name: str, agent_id: int, recipe_id: int, trigger_type: str="manual", trigger_value: Optional[int]=None):
    wf = WorkflowDef(name=name, agent_id=agent_id, recipe_id=recipe_id, trigger_type=trigger_type, trigger_value=trigger_value, status="yellow", enabled=1)
    if trigger_type == "interval" and trigger_value:
        wf.next_run_at = datetime.utcnow() + timedelta(minutes=trigger_value)
    db.add(wf); db.commit(); db.refresh(wf); return wf

def update_workflow(db: Session, wf_id: int, **kwargs):
    wf = db.query(WorkflowDef).filter(WorkflowDef.id==wf_id).first()
    if not wf: return None
    for k, v in kwargs.items():
        if hasattr(wf, k) and v is not None:
            setattr(wf, k, v)
    db.commit(); db.refresh(wf); return wf

def delete_workflow(db: Session, wf_id: int) -> bool:
    wf = db.query(WorkflowDef).filter(WorkflowDef.id==wf_id).first()
    if not wf: return False
    db.delete(wf); db.commit(); return True

def compute_status(wf: WorkflowDef) -> str:
    if not wf.last_run_at: return "yellow"
    delta = datetime.utcnow() - wf.last_run_at
    if delta.total_seconds() <= 24*3600: return "green"
    if delta.total_seconds() <= 7*24*3600: return "yellow"
    return "red"

def run_now(db: Session, wf_id: int):
    wf = db.query(WorkflowDef).filter(WorkflowDef.id==wf_id).first()
    if not wf: return None
    run = execute_recipe_run(db, agent_id=wf.agent_id, recipe_id=wf.recipe_id)
    wf.last_run_at = datetime.utcnow()
    wf.status = compute_status(wf)
    if wf.trigger_type == "interval" and wf.trigger_value:
        wf.next_run_at = datetime.utcnow() + timedelta(minutes=wf.trigger_value)
    db.commit(); db.refresh(wf)
    return run

def tick(db: Session) -> int:
    now = datetime.utcnow()
    due = db.query(WorkflowDef).filter(WorkflowDef.enabled==1, WorkflowDef.trigger_type=="interval", WorkflowDef.next_run_at != None, WorkflowDef.next_run_at <= now).all()
    count = 0
    for wf in due:
        run_now(db, wf.id); count += 1
    return count
