<img width="385" height="272" alt="ipav_agentic av -blue" src="https://github.com/user-attachments/assets/72269dd8-a9fc-40fc-9325-df14917c0658" />

**The Agentic Ops IPAV application provides a suite of features for creating AI-driven operational workflows using NLP, MCP and converting SOP's into agentic recipes YAML and JSON.**

**Try Demo Now:**
https://agentic-ops-ipav.streamlit.app/

**Do NOT Save Key in Online Demo!**


**Local Development Tips**

To run the application locally:

**Clone the repository:**
# Make sure IPAV-Agents branch selected
git clone https://github.com/AgentAiDrive/AV-AIops/tree/IPAV-Agents/sma-av-streamlit.git
cd AV-AIops

Create a virtual environment and install dependencies:
python3 -m venv venv
source venv/bin/activate
pip install -r sma-av-streamlit/requirements.txt

**Run the app:**
streamlit run sma-av-streamlit/app.py --server.port 8501

Open http://localhost:8501 in your browser. Follow the steps described in the runbook to seed the database, create agents, author recipes and test connectors.

For development, use core/mcp/scaffold.py to generate new connectors and ensure the template functions are defined. 
