<img width="120" height="89" alt="ipav_agentic av -blue" src="https://github.com/user-attachments/assets/00c68a1d-224f-4170-b44f-9982bf4b5e8d" />
**The Agentic Ops IPAV application provides a suite of features for creating AI-driven operational workflows using NLP, MCP and converting SOP's into agentic recipes YAML and JSON.**

**Try Demo Now:**
https://agentic-ops-ipav.streamlit.app/

**Do NOT Save Key in Online Demo!**


**Local Development Tips**

To run the application locally:

**Clone the repository:**
# Make sure IPAV-Agents branch selected
git clone https://github.com/AgentAiDrive/AV-AIops/sma-av-streamlit.git
cd AV-AIops

Create a virtual environment and install dependencies:
python3 -m venv venv
source venv/bin/activate
pip install -r sma-av-streamlit/requirements.txt

**Run the app:**
streamlit run sma-av-streamlit/app.py --server.port 8501

Open http://localhost:8501 in your browser. Follow the steps described in the runbook to seed the database, create agents, author recipes and test connectors.

For development, use core/mcp/scaffold.py to generate new connectors and ensure the template functions are defined. 
