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
    wfs = list_workflows(db)
    existing_names = {wf.name.lower(): wf.id for wf in wfs}

    colL, colR = st.columns([1, 3])
    if colL.button("⏱️ Tick scheduler"):
        n = tick(db)
        st.toast(f"Ticked. Ran {n} workflow(s).")

    # --- New Workflow (ID-based, avoid ORM instances in widget state) ---
    st.subheader("New Workflow")

    agent_opts = {a.id: a.name for a in db.query(Agent).order_by(Agent.name).all()}
    recipe_opts = {r.id: r.name for r in db.query(Recipe).order_by(Recipe.name).all()}

    with st.form("new_wf"):
        name = st.text_input("Name", help="Workflow names must be unique (case-insensitive).")

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

    if ok:
        clean = " ".join((name or "").split())
        errors = []
        if not clean:
            errors.append("Please provide a workflow name.")
        elif clean.lower() in existing_names:
            errors.append(f"Workflow '{clean}' already exists. Pick another name.")

        if agent_id is None:
            errors.append("Select an agent for the workflow.")
        if recipe_id is None:
            errors.append("Select a recipe for the workflow.")

        if not agent_opts:
            st.info("Add an agent on the 🤖 Agents page before creating workflows.")
        if not recipe_opts:
            st.info("Create a recipe on the 📜 Recipes page before creating workflows.")

        if errors:
            for msg in errors:
                st.error(msg)
        else:
            try:
                create_workflow(
                    db,
                    name=clean,
                    agent_id=int(agent_id),
                    recipe_id=int(recipe_id),
                    trigger_type=trig,
                    trigger_value=int(minutes) if minutes else None,
                )
                st.success("Workflow created.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Failed to create workflow: {type(e).__name__}: {e}")

    # --- Existing Workflows ---
    st.subheader("Workflows")
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
                        try:
                            with st.spinner("Executing workflow..."):
                                run = run_now(db, wf.id)
                            st.toast(f"Run {run.id} completed.", icon="✅")
                        except Exception as e:
                            st.error(f"Run failed: {type(e).__name__}: {e}")

                with cols[1]:
                    enabled = bool(wf.enabled)
                    if st.button("Enable" if not enabled else "Disable", key=f"en-{wf.id}"):
                        update_workflow(db, wf.id, enabled=0 if enabled else 1)
                        st.rerun()

                with cols[2]:
                    with st.popover("Rename"):
                        with st.form(f"rename-{wf.id}"):
                            new = st.text_input("New name", value=wf.name)
                            save = st.form_submit_button("Save")
                        if save:
                            candidate = " ".join((new or "").split())
                            if not candidate:
                                st.error("Workflow name cannot be empty.")
                            elif candidate.lower() in existing_names and existing_names[candidate.lower()] != wf.id:
                                st.error(f"Workflow '{candidate}' already exists.")
                            elif candidate == wf.name:
                                st.info("Name unchanged.")
                            else:
                                try:
                                    update_workflow(db, wf.id, name=candidate)
                                    st.success("Workflow renamed.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Rename failed: {type(e).__name__}: {e}")

                with cols[3]:
                    if st.button("Delete", key=f"del-{wf.id}"):
                        delete_workflow(db, wf.id)
                        st.rerun()

                cols[4].write(f"Last: {wf.last_run_at or '—'} · Next: {wf.next_run_at or '—'} · Status: {status}")

                with st.expander("Configuration", expanded=False):
                    with st.form(f"cfg-{wf.id}"):
                        agent_choice = st.selectbox(
                            "Agent",
                            options=list(agent_opts.keys()),
                            format_func=lambda i: agent_opts[i],
                            index=list(agent_opts.keys()).index(wf.agent_id) if wf.agent_id in agent_opts else 0,
                            key=f"agent-{wf.id}"
                        ) if agent_opts else None

                        recipe_choice = st.selectbox(
                            "Recipe",
                            options=list(recipe_opts.keys()),
                            format_func=lambda i: recipe_opts[i],
                            index=list(recipe_opts.keys()).index(wf.recipe_id) if wf.recipe_id in recipe_opts else 0,
                            key=f"recipe-{wf.id}"
                        ) if recipe_opts else None

                        trig_choice = st.selectbox(
                            "Trigger",
                            ["manual", "interval"],
                            index=0 if wf.trigger_type == "manual" else 1,
                            key=f"trig-{wf.id}"
                        )
                        interval_val = None
                        if trig_choice == "interval":
                            interval_val = st.number_input(
                                "Interval minutes",
                                min_value=1,
                                value=int(wf.trigger_value or 60),
                                key=f"interval-{wf.id}"
                            )

                        submitted = st.form_submit_button("Update workflow")

                    if submitted:
                        updates = {}
                        if agent_choice is not None and agent_choice != wf.agent_id:
                            updates["agent_id"] = int(agent_choice)
                        if recipe_choice is not None and recipe_choice != wf.recipe_id:
                            updates["recipe_id"] = int(recipe_choice)
                        if trig_choice != wf.trigger_type:
                            updates["trigger_type"] = trig_choice
                        if trig_choice == "interval":
                            updates["trigger_value"] = int(interval_val or wf.trigger_value or 60)
                        else:
                            updates["trigger_value"] = None

                        if not updates:
                            st.info("No changes detected.")
                        else:
                            try:
                                update_workflow(db, wf.id, **updates)
                                st.success("Workflow updated.")
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))
                            except Exception as e:
                                st.error(f"Update failed: {type(e).__name__}: {e}")

# Optional: link to a dashboard page if you have one
# st.page_link("pages/07_Dashboard.py", label="📊 Open Dashboard")
