
from __future__ import annotations
import os, json
from sqlalchemy.orm import Session
from .session import engine, get_session
from .models import Base, Agent, Recipe, Tool

RECIPES_DIR = os.path.join(os.getcwd(), "recipes")
REGISTRY = {
    "slack-bot": {"description":"Slack bot MCP tool", "endpoint":"http://localhost:3001"},
    "zoom-admin": {"description":"Zoom admin MCP tool", "endpoint":"http://localhost:3002"},
    "servicenow": {"description":"ServiceNow MCP tool", "endpoint":"http://localhost:3003"},
}

def init_db():
    Base.metadata.create_all(bind=engine)

def seed_demo():
    init_db()
    with get_session() as db:
        for name, domain in [("Support","support"),("Events","events"),("Device Monitoring","device-monitoring")]:
            if not db.query(Agent).filter(Agent.name==name).first():
                db.add(Agent(name=name, domain=domain, config_json={}))
        # recipes in folder
        if os.path.isdir(RECIPES_DIR):
            for fn in os.listdir(RECIPES_DIR):
                if fn.endswith(".yaml"):
                    name = fn.replace(".yaml","").replace("_"," ").title()
                    if not db.query(Recipe).filter(Recipe.name==name).first():
                        db.add(Recipe(name=name, yaml_path=fn))
        # tools registry
        for k, v in REGISTRY.items():
            if not db.query(Tool).filter(Tool.name==k).first():
                db.add(Tool(name=k, description=v["description"], endpoint=v["endpoint"]))
        db.commit()
