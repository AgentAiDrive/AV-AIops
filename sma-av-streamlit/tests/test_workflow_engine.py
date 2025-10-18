from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.db.models import Agent, Base, Recipe, Run
from core.workflow.engine import execute_recipe_run


@pytest.fixture()
def db_session(tmp_path):
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_execute_recipe_run_missing_agent(db_session):
    recipe = Recipe(name="Test Recipe", yaml_path="backup_room_failover.yaml")
    db_session.add(recipe)
    db_session.commit()

    with pytest.raises(ValueError, match="Agent 42 not found"):
        execute_recipe_run(db_session, agent_id=42, recipe_id=recipe.id)

    assert db_session.query(Run).count() == 0


def test_execute_recipe_run_missing_recipe(db_session):
    agent = Agent(name="Test Agent", domain="testing", config_json={})
    db_session.add(agent)
    db_session.commit()

    with pytest.raises(ValueError, match="Recipe 99 not found"):
        execute_recipe_run(db_session, agent_id=agent.id, recipe_id=99)

    assert db_session.query(Run).count() == 0


def test_execute_recipe_run_creates_evidence(db_session):
    agent = Agent(name="Test Agent", domain="testing", config_json={})
    recipe = Recipe(name="Test Recipe", yaml_path="backup_room_failover.yaml")
    db_session.add_all([agent, recipe])
    db_session.commit()

    run = execute_recipe_run(db_session, agent_id=agent.id, recipe_id=recipe.id)

    refreshed = db_session.get(Run, run.id)
    assert refreshed is not None
    assert refreshed.status == "completed"
    assert len(refreshed.evidence) == 4
    phases = {ev.payload.get("phase") for ev in refreshed.evidence}
    assert phases == {"intake", "plan", "act", "verify"}
