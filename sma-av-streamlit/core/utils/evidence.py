
from __future__ import annotations
from sqlalchemy.orm import Session
from ..db.models import Evidence

def attach_json(db: Session, run_id: int, payload: dict):
    ev = Evidence(run_id=run_id, payload=payload)
    db.add(ev); db.commit()
    return ev
