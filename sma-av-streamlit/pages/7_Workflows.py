# pages/7_🧩_Workflows.py
import streamlit as st
from core.db.session import get_session
from core.db.seed import init_db
from core.db.models import Agent, Recipe
from core.workflow.service import (
    list_workflows, create_workflow, update_workflow, delete_workflow,
    run_now, compute_status, tick
)
# paste this at the top of any page
import streamlit as st
from core.ui.page_tips import show as show_tip

PAGE_KEY = "Workflows"  # <= change per page: "Setup Wizard" | "Settings" | "Chat" | "Agents" | "Recipes" | "MCP Tools" | "Workflows" | "Dashboard"
show_tip(PAGE_KEY)

st.title("🧩 Workflows")
init_db()

with get_session() as db:  # keep DB open for the whole page render
    colL, colR = st.columns([1, 3])
    if colL.button("⏱️ Tick scheduler"):
        n = tick(db)
        st.toast(f"Ticked. Ran {n} workflow(s).")

    # --- New Workflow (ID-based, avoid ORM instances in widget state) ---
    st.subheader("New Workflow")

    agent_opts = {a.id: a.name for a in db.query(Agent).order_by(Agent.name).all()}
    recipe_opts = {r.id: r.name for r in db.query(Recipe).order_by(Recipe.name).all()}

    with st.form("new_wf"):
        name = st.text_input("Name")

        agent_id = (
            st.selectbox(
                "Agent",
                options=list(agent_opts.keys()),
                format_func=lambda i: agent_opts[i],
            ) if agent_opts else None
        )

        recipe_id = (
            st.selectbox(
                "Recipe",
                options=list(recipe_opts.keys()),
                format_func=lambda i: recipe_opts[i],
            ) if recipe_opts else None
        )

        trig = st.selectbox("Trigger", ["manual", "interval"])
        minutes = st.number_input("Interval minutes", min_value=1, value=60) if trig == "interval" else None

        ok = st.form_submit_button("Create Workflow")

    if ok and name and agent_id is not None and recipe_id is not None:
        create_workflow(
            db,
            name=name,
            agent_id=int(agent_id),
            recipe_id=int(recipe_id),
            trigger_type=trig,
            trigger_value=int(minutes) if minutes else None,
        )
        st.success("Workflow created.")
        st.rerun()

    # --- Existing Workflows ---
    st.subheader("Workflows")
    wfs = list_workflows(db)
    if not wfs:
        st.info("No workflows yet.")
    else:
        for wf in wfs:
            status = compute_status(wf)
            color = {"green": "🟢", "yellow": "🟡", "red": "🔴"}[status]

            with st.container(border=True):
                top = st.columns([6, 1])
                top[0].markdown(
                    f"""**{wf.name}**  
Agent ID: `{wf.agent_id}` · Recipe ID: `{wf.recipe_id}`  
Trigger: `{wf.trigger_type}` {wf.trigger_value or ''}"""
                )
                top[1].markdown(
                    f"<div style='text-align:right;font-size:24px'>{color}</div>",
                    unsafe_allow_html=True,
                )

                cols = st.columns([1, 1, 1, 1, 3])

                with cols[0]:
                    if st.button("Run now", key=f"run-{wf.id}"):
                        run = run_now(db, wf.id)
                        st.toast(f"Run {run.id} completed.", icon="✅")

                with cols[1]:
                    enabled = bool(wf.enabled)
                    if st.button("Enable" if not enabled else "Disable", key=f"en-{wf.id}"):
                        update_workflow(db, wf.id, enabled=0 if enabled else 1)
                        st.rerun()

                with cols[2]:
                    with st.popover("Rename"):  # popover has no key=
                        new = st.text_input("New name", key=f"nm-{wf.id}")
                        if st.button("Save", key=f"sv-{wf.id}") and new:
                            update_workflow(db, wf.id, name=new)
                            st.rerun()

                with cols[3]:
                    if st.button("Delete", key=f"del-{wf.id}"):
                        delete_workflow(db, wf.id)
                        st.rerun()

                cols[4].write(f"Last: {wf.last_run_at or '—'} · Next: {wf.next_run_at or '—'} · Status: {status}")

# Optional: link to a dashboard page if you have one
# st.page_link("pages/07_Dashboard.py", label="📊 Open Dashboard")
