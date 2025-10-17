
# SMA AV‑AI Ops (Streamlit)

Python-only Streamlit app for AV Ops orchestration. No Docker, Node, or Next.js required.

## Quickstart

```bash
python -m venv .venv
# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt

# (optional) set secrets
cp .streamlit/secrets.toml.sample .streamlit/secrets.toml

streamlit run app.py
```

## New features
- **/sop** in Chat: paste a SOP/runbook → model (or heuristic) converts to YAML recipe → attaches to (or creates) an agent → auto-discovers/scaffolds tools mentioned → runs the workflow.
- **Workflows page**: CRUD for workflow definitions with manual/interval triggers, enable/disable, Run Now, and green/yellow/red status chip.

Database file: `sma_av_ai_ops.db` in the project root.


cd 
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt


1_🏁_Setup_Wizard
2_💬_Chat
3_🤖_Agents
4_📜_Recipes
5_🧰_MCP_Tools
6_⚙️_Settings
7_🧩_Workflows
8_Dashboard
