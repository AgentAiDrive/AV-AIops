from __future__ import annotations
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db.models import WorkflowDef
from .engine import execute_recipe_run

# Import the shared run-store helper
from core.runstore_factory import make_runstore, record_run_start, record_run_finish


def list_workflows(db: Session):
    return db.query(WorkflowDef).order_by(WorkflowDef.id.asc()).all()


def _workflow_name_exists(db: Session, name: str, *, exclude_id: Optional[int] = None) -> bool:
    q = db.query(WorkflowDef.id).filter(func.lower(WorkflowDef.name) == name.lower())
    if exclude_id is not None:
        q = q.filter(WorkflowDef.id != exclude_id)
    return q.first() is not None


def create_workflow(
    db: Session,
    name: str,
    agent_id: int,
    recipe_id: int,
    trigger_type: str = "manual",
    trigger_value: Optional[int] = None,
):
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
        if new_name.lower() != wf.name.lower():
            if _workflow_name_exists(db, new_name, exclude_id=wf_id):
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
    Trigger a workflow immediately.  Records the run in RunStore with
    'running' at start and then 'success' or 'failed' at finish.
    """
    wf = db.query(WorkflowDef).filter(WorkflowDef.id == wf_id).first()
    if not wf:
        return None

    # Write a 'running' record to RunStore
    store = make_runstore()
    started_dt = datetime.now(timezone.utc)
    # Use a generated UUID as the run id; adopt the engine's id if it exists
    run_id = f"{uuid4()}"
    record_run_start(
        store,
        run_id=run_id,
        name=wf.name,
        agent_id=wf.agent_id,
        recipe_id=wf.recipe_id,
        trigger="manual",
        started_at=started_dt,
    )

    err_msg = None
    status = "success"
    run = None
    try:
        run = execute_recipe_run(db, agent_id=wf.agent_id, recipe_id=wf.recipe_id)
        # If the engine returns an id, use it instead
        engine_id = (
            getattr(run, "id", None)
            or getattr(run, "run_id", None)
            or (run.get("id") if isinstance(run, dict) else None)
            or (run.get("run_id") if isinstance(run, dict) else None)
        )
        if engine_id:
            run_id = str(engine_id)
    except Exception as e:
        status = "failed"
        err_msg = f"{type(e).__name__}: {e}"
        # Record failure before re-raising to make the dashboard reflect the failure
        record_run_finish(
            store,
            run_id=run_id,
            status=status,
            error=err_msg,
            started_at=started_dt,
        )
        raise
    finally:
        # Record success if no error occurred
        if err_msg is None:
            record_run_finish(
                store,
                run_id=run_id,
                status=status,
                error=None,
                started_at=started_dt,
            )

    # Update workflow timestamps/status
    wf.last_run_at = datetime.utcnow()
    wf.status = compute_status(wf)
    if wf.trigger_type == "interval" and wf.trigger_value:
        wf.next_run_at = datetime.utcnow() + timedelta(minutes=wf.trigger_value)
    db.commit()
    db.refresh(wf)
    return run


def tick(db: Session) -> int:
    """Run all due interval workflows.  Returns number of workflows run."""
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
