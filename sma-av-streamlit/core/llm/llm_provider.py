import os

def get_provider():
    return (os.getenv("LLM_PROVIDER") or "openai").lower()

def pick_model(session_state) -> str:
    p = (session_state.get("llm_provider") or "OpenAI").lower()
    if p == "anthropic":
        return "claude-3-5-sonnet-latest"  # adjust as needed
    return "gpt-4o-mini"                  # or "gpt-4.1" / "gpt-4o"
