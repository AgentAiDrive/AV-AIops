# pages/3_Agents.py
import streamlit as st
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from core.db.session import get_session
from core.db.models import Agent, Recipe
from core.workflow.engine import execute_recipe_run

st.set_page_config(page_title="Agents", page_icon="🤖", layout="wide")
st.title("🤖 Agents")

st.markdown(
    """
    <style>
    .agent-scroll {max-height: 480px; overflow-y: auto; scroll-behavior: smooth; padding-right: 0.5rem;}
    .agent-card {margin-bottom: 1rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

def _clean(s: str | None) -> str:
    return " ".join((s or "").strip().split())

def _dup_exists(db, name: str) -> Agent | None:
    # case-insensitive duplicate check
    return db.query(Agent).filter(func.lower(Agent.name) == name.lower()).first()

def _friendly_integrity_message(e: IntegrityError, name: str) -> str:
    # Try to pull the underlying DB-API message (SQLite: "UNIQUE constraint failed: ...")
    msg = ""
    if getattr(e, "orig", None) and getattr(e.orig, "args", None):
        try:
            msg = " ".join(str(a) for a in e.orig.args if a)
        except Exception:
            msg = str(e.orig) or str(e)
    if "unique" in msg.lower() or "constraint" in msg.lower():
        return f"Agent '{name}' conflicts with an existing record (likely a duplicate name)."
    if "not null" in msg.lower():
        return "A required field was empty (check Name and Domain)."
    return "Database constraint error. Check logs for details."

with get_session() as db:  # type: ignore
    st.subheader("Create Agent")

    col1, col2 = st.columns(2)
    with col1:
        name_input = st.text_input("Name", placeholder="e.g., Support")
    with col2:
        domain_input = st.text_input("Domain", placeholder="e.g., support")

    if st.button("Add Agent"):
        name = _clean(name_input)
        domain = _clean(domain_input)

        if not name or not domain:
            st.warning("Please provide both **Name** and **Domain**.")
        else:
            # Fast path: if exists (case-insensitive), don’t attempt insert
            existing = _dup_exists(db, name)
            if existing:
                st.info(f"Agent **{existing.name}** already exists (id={existing.id}).")
            else:
                try:
                    with st.spinner("Creating agent..."):
                        db.add(Agent(name=name, domain=domain, config_json={}))
                        db.commit()
                    st.success(f"Agent **{name}** created.")
                except IntegrityError as e:
                    db.rollback()
                    st.error(_friendly_integrity_message(e, name))
                except Exception as e:
                    db.rollback()
                    st.error(f"Unexpected error creating agent: {type(e).__name__}: {e}")

    st.divider()
    st.subheader("Agents")

    agents = db.query(Agent).order_by(Agent.name).all()
    recipes = db.query(Recipe).order_by(Recipe.name).all()

    search_query = st.text_input("Filter agents", placeholder="Search by name or domain...")
    recipe_filter = st.text_input("Filter recipes", placeholder="Filter recipe names for selection...")

    filtered_agents = agents
    if search_query:
        term = search_query.lower()
        filtered_agents = [
            a for a in agents if term in a.name.lower() or term in (a.domain or "").lower()
        ]

    filtered_recipes = recipes
    if recipe_filter:
        rterm = recipe_filter.lower()
        filtered_recipes = [r for r in recipes if rterm in r.name.lower()]

    if not filtered_agents:
        st.info("No agents match your filter.")
    else:
        st.markdown("<div class='agent-scroll'>", unsafe_allow_html=True)
        for a in filtered_agents:
            with st.container(border=True):
                st.markdown(f"<div class='agent-card'><strong>{a.name}</strong> · `{a.domain}`</div>", unsafe_allow_html=True)
                cols = st.columns([2, 2, 2])
                rec = (
                    cols[0].selectbox(
                        "Recipe",
                        filtered_recipes,
                        format_func=lambda r: r.name,
                        key=f"r-{a.id}"
                    )
                    if filtered_recipes
                    else None
                )

                if cols[1].button("Trigger Run", key=f"run-{a.id}"):
                    if not rec:
                        st.warning("Choose a recipe first.")
                    else:
                        try:
                            with st.spinner("Executing run..."):
                                run = execute_recipe_run(db, agent_id=a.id, recipe_id=rec.id)
                            st.toast(f"Run {getattr(run, 'id', '—')} completed.", icon="✅")
                        except Exception as e:
                            st.error(f"Run failed: {type(e).__name__}: {e}")

                if cols[2].button("Delete", key=f"del-{a.id}"):
                    try:
                        with st.spinner("Removing agent..."):
                            db.delete(a)
                            db.commit()
                        st.rerun()
                    except IntegrityError as e:
                        db.rollback()
                        st.error("Cannot delete this agent due to database constraints.")
                    except Exception as e:
                        db.rollback()
                        st.error(f"Delete failed: {type(e).__name__}: {e}")
        st.markdown("</div>", unsafe_allow_html=True)
