
import streamlit as st
from core.llm.client import chat
from core.recipes.from_sop import sop_to_recipe_yaml
from core.recipes.attach import attach_recipe_to_agent
from core.mcp.from_sop_tools import ensure_tools_for_sop
from core.db.session import get_session
from core.workflow.engine import execute_recipe_run

st.title("💬 Chat")
with st.sidebar:
    st.subheader("Task helpers")
    st.markdown("Use **/sop** to convert text → recipe → attach → run. Example:")
    st.code("/sop Agent=Support Name=Projector Reset\nSteps:\n- Gather room_id\n- Reset projector\n- Verify image via Slack")
    json_mode = st.checkbox("JSON mode", value=False)

if "conversation" not in st.session_state:
    st.session_state["conversation"] = [{"role":"system", "content":"You are an AV operations assistant."}]

def _render_messages():
    for m in st.session_state["conversation"]:
        with st.chat_message(m["role"] if m["role"] != "system" else "assistant"):
            st.write(m["content"])

def _handle_sop(text: str):
    import re, os
    agent = re.search(r"Agent=([^\n]+)", text)
    name = re.search(r"Name=([^\n]+)", text)
    agent_name = (agent.group(1).strip() if agent else "Support")
    recipe_name = (name.group(1).strip() if name else "Generated Recipe")
    sop_body = text.split("\n", 1)[1] if "\n" in text else text
    ok, yml = sop_to_recipe_yaml(sop_body, name_hint=recipe_name)
    tools, created = ensure_tools_for_sop(os.getcwd(), sop_body)
    with get_session() as db:  # type: ignore
        a, r = attach_recipe_to_agent(db, agent_name, recipe_name, yml)
        run = execute_recipe_run(db, agent_id=a.id, recipe_id=r.id)
        return a.name, r.name, tools, created, yml, run.id

_render_messages()

prompt = st.chat_input("Type your message (/sop ... to build & run from SOP)")
if prompt:
    st.session_state["conversation"].append({"role":"user", "content":prompt})
    if prompt.strip().lower().startswith("/sop"):
        with st.chat_message("assistant"):
            with st.spinner("Generating recipe, attaching to agent, ensuring tools, running..."):
                agent_name, recipe_name, tools, created, yml, run_id = _handle_sop(prompt)
                st.success(f"Recipe **{recipe_name}** attached to agent **{agent_name}**. Run {run_id} completed.")
                if tools:
                    st.write("Tools referenced:", tools)
                if created:
                    st.write("New tools scaffolded:", created)
                with st.expander("Generated YAML"):
                    st.code(yml, language="yaml")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply = chat(st.session_state["conversation"], json_mode=json_mode)
                st.write(reply)
        st.session_state["conversation"].append({"role":"assistant","content":reply})
