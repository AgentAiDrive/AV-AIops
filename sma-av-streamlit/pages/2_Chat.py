import os
import re
import streamlit as st

from core.llm.client import chat  # your existing chat() function
from core.recipes.from_sop import sop_to_recipe_yaml
from core.recipes.attach import attach_recipe_to_agent
from core.mcp.from_sop_tools import ensure_tools_for_sop
from core.db.session import get_session
from core.workflow.engine import execute_recipe_run
import streamlit as st
from core.ui.page_tips import show as show_tip

PAGE_KEY = "Chat"  # <= change per page: "Setup Wizard" | "Settings" | "Chat" | "Agents" | "Recipes" | "MCP Tools" | "Workflows" | "Dashboard"
show_tip(PAGE_KEY)
# New: robust secret handling + provider selection
from core.secrets import get_active_key, is_mock_enabled, pick_active_provider

st.title("💬 Chat")

# --- Sidebar helpers ---------------------------------------------------------
with st.sidebar:
    st.subheader("Task helpers")
    st.markdown("Use **/sop** to convert text → recipe → attach → run. Example:")
    st.code("/sop Agent=Support Name=Projector Reset\nSteps:\n- Gather_room\n- Reset projector\n- Verify image via Slack")
    json_mode = st.checkbox("JSON mode (raw tool payloads)", value=False)

# --- Resolve active provider + key (NO silent fallback) ----------------------
provider_key, provider_name, key_source = get_active_key()  # ('openai'|'anthropic') and the key + source string
mcp_mock = is_mock_enabled()  # for MCP tools only; chat will not auto-mock

def _mask(k: str | None) -> str:
    if not k:
        return "missing"
    if len(k) <= 8:
        return "••••"
    return f"••••{k[-4:]}"

st.caption(
    f"Model: {('🟢' if provider_name=='openai' else '🔵')} {provider_name} • "
    f"key source: {key_source} • MCP mock: {mcp_mock}"
)

# Export to environment so core.llm.client can pick them up (without refactor)
# We do NOT store secrets in session. We just expose what the chosen provider needs.
os.environ["LLM_PROVIDER"] = provider_name
if provider_name == "openai":
    if provider_key:
        os.environ["OPENAI_API_KEY"] = provider_key
else:
    if provider_key:
        os.environ["ANTHROPIC_API_KEY"] = provider_key

# --- Conversation state ------------------------------------------------------
if "conversation" not in st.session_state:
    st.session_state["conversation"] = [
        {"role": "system", "content": "You are an AV operations assistant."}
    ]

def _render_messages():
    for m in st.session_state["conversation"]:
        with st.chat_message(m["role"] if m["role"] != "system" else "assistant"):
            # Avoid dumping system role literally; show as assistant context
            if m["role"] == "system":
                st.write(f"_{m['content']}_")
            else:
                st.write(m["content"])

# --- /sop pipeline -----------------------------------------------------------
def _handle_sop(text: str):
    agent = re.search(r"Agent=([^\n]+)", text)
    name = re.search(r"Name=([^\n]+)", text)
    agent_name = (agent.group(1).strip() if agent else "Support")
    recipe_name = (name.group(1).strip() if name else "Generated Recipe")

    # Strip first line (with /sop and keyvals) if present; pass the body to SOP→Recipe
    sop_body = text.split("\n", 1)[1] if "\n" in text else text

    ok, yml = sop_to_recipe_yaml(sop_body, name_hint=recipe_name)
    if not ok:
        raise RuntimeError("Failed to generate recipe YAML from SOP.")

    # Scaffold any missing MCP tool stubs implied by SOP text
    tools, created = ensure_tools_for_sop(os.getcwd(), sop_body)

    # Attach recipe to agent and execute a run
    with get_session() as db:  # type: ignore
        a, r = attach_recipe_to_agent(db, agent_name, recipe_name, yml)
        run = execute_recipe_run(db, agent_id=a.id, recipe_id=r.id)
        return a.name, r.name, tools, created, yml, getattr(run, "id", None)

# --- LLM call helper (no auto-mock) -----------------------------------------
def _llm_reply(messages: list[dict], json_mode: bool) -> str:
    """
    Calls your core.llm.client.chat(...) with the chosen provider.
    Fails loudly if keys are missing or provider call fails. Does NOT auto-mock.
    """
    if not provider_key:
        raise RuntimeError(
            f"No API key available for {provider_name}. "
            f"Set Streamlit secrets or provide an env var. (source tried: {key_source})"
        )
    # core.llm.client.chat should read provider from env or session.
    # We already set LLM_PROVIDER and the correct API key in os.environ above.
    return chat(messages, json_mode=json_mode)

# --- UI rendering + interaction ---------------------------------------------
_render_messages()

prompt = st.chat_input("Type your message (/sop ... to build & run from SOP)")
if prompt:
    st.session_state["conversation"].append({"role": "user", "content": prompt})

    # Handle /sop shortcut
    if prompt.strip().lower().startswith("/sop"):
        with st.chat_message("assistant"):
            with st.spinner("Generating recipe, attaching to agent, ensuring tools, running..."):
                try:
                    agent_name, recipe_name, tools, created, yml, run_id = _handle_sop(prompt)
                    st.success(f"Recipe **{recipe_name}** attached to agent **{agent_name}**. Run {run_id} completed.")
                    if tools:
                        st.write("Tools referenced:", tools)
                    if created:
                        st.write("New tools scaffolded:", created)
                    with st.expander("Generated YAML", expanded=False):
                        st.code(yml, language="yaml")
                except Exception as e:
                    st.error(f"SOP pipeline failed: {type(e).__name__}: {e}")
    else:
        with st.chat_message("assistant"):
            try:
                with st.spinner("Thinking..."):
                    reply = _llm_reply(st.session_state["conversation"], json_mode=json_mode)
                st.write(reply)
                st.session_state["conversation"].append({"role": "assistant", "content": reply})
            except Exception as e:
                # Show the reason (keys missing, network error, quota, etc.)
                st.error(f"LLM call failed: {type(e).__name__}: {e}")
                # Optionally: provide a quick hint
                with st.expander("Troubleshoot", expanded=False):
                    st.markdown(
                        "- Confirm **Settings → provider** matches your intended model\n"
                        "- In Streamlit Cloud, set secrets as either:\n"
                        "  - `OPENAI_API_KEY = sk-...` **or** `[openai] api_key='sk-...'`\n"
                        "  - `ANTHROPIC_API_KEY = ...` **or** `[anthropic] api_key='...'`\n"
                        "- Make sure you didn’t save blank overrides in Settings\n"
                        "- Check network egress and org policy for outbound API calls"
                    )
                with st.expander("LLM self-test (temporary)"):
                    try:
                        t = chat([{"role":"system","content":"You are test."},{"role":"user","content":"Say 'real' if this is a real provider call."}], json_mode=False)
                        st.success("Provider call succeeded.")
                        st.code(t)
                    except Exception as e:
                        st.error(f"Provider call failed: {type(e).__name__}: {e}")
