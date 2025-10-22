
<img width="93" height="70" alt="ipav_agentic av" src="https://github.com/user-attachments/assets/7b26b308-8419-476d-af95-0e7d1844dd9d" />

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
