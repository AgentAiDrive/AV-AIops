
import streamlit as st
from core.db.seed import seed_demo
# paste this at the top of any page
import streamlit as st
from core.ui.page_tips import show as show_tip

PAGE_KEY = "Setup Wizard"  # <= change per page: "Setup Wizard" | "Settings" | "Chat" | "Agents" | "Recipes" | "MCP Tools" | "Workflows" | "Dashboard"
show_tip(PAGE_KEY)

st.title("🏁 Setup Wizard")
st.write("Initialize database, seed demo agents, tools, and recipes.")

if st.button("Initialize database & seed demo data"):
    seed_demo()
    st.success("Seed complete.")
