# pages/<your_agents_page>.py  (e.g., sma-av-streamlit/pages/03_Agents.py)
import streamlit as st
from core.db.session import get_session
from core.db.models import Agent, Recipe
from core.workflow.engine import execute_recipe_run
from core.runs_store import RunStore
# paste this at the top of any page
import streamlit as st
from core.ui.page_tips import show as show_tip

PAGE_KEY = "Agents"  # <= change per page: "Setup Wizard" | "Settings" | "Chat" | "Agents" | "Recipes" | "MCP Tools" | "Workflows" | "Dashboard"
show_tip(PAGE_KEY)

st.title("🤖 Agents")

store = RunStore()

with get_session() as db:  # type: ignore
    st.subheader("Create Agent")
    name = st.text_input("Name")
    domain = st.text_input("Domain")
    if st.button("Add Agent") and name and domain:
        if not db.query(Agent).filter(Agent.name == name).first():
            db.add(Agent(name=name, domain=domain, config_json={}))
            db.commit()
            st.success("Agent created.")
        else:
            st.warning("Agent exists.")
    st.divider()

    st.subheader("Agents")
    agents = db.query(Agent).all()
    recipes = db.query(Recipe).all()
    for a in agents:
        with st.container(border=True):
            st.markdown(f"""**{a.name}** · `{a.domain}`""")
            cols = st.columns([2, 2, 2])
            rec = cols[0].selectbox(
                "Recipe",
                recipes,
                format_func=lambda r: r.name,
                key=f"r-{a.id}",
            ) if recipes else None

            if cols[1].button("Trigger Run", key=f"run-{a.id}") and rec:
                with store.workflow_run(
                    workflow_id=f"agent:{a.id}",
                    name=f"Agent {a.name}",
                    agent_id=a.id,
                    recipe_id=rec.id if rec else None,
                    trigger="manual",
                    meta={"page": "Agents"},
                ) as log:
                    log.step("intake", "Preparing agent execution", payload={"agent": a.name, "recipe": rec.name if rec else None})
                    log.step("plan", "Calling core.workflow.engine.execute_recipe_run")
                    db_run = execute_recipe_run(db, agent_id=a.id, recipe_id=rec.id)  # your engine
                    log.artifact(
                        "run",
                        "DB run record",
                        external_id=str(getattr(db_run, "id", "")),
                        data={"status": getattr(db_run, "status", None)},
                    )
                    log.step("act", "Execution finished in engine", result={"db_run_id": getattr(db_run, "id", None)})
                    log.step("verify", "Post checks passed")

                st.toast("Run completed and logged.", icon="✅")

            if cols[2].button("Delete", key=f"del-{a.id}"):
                db.delete(a)
                db.commit()
                st.rerun()
