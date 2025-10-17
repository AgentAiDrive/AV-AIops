
import streamlit as st
from core.db.seed import seed_demo

st.title("🏁 Setup Wizard")
st.write("Initialize database, seed demo agents, tools, and recipes.")

if st.button("Initialize database & seed demo data"):
    seed_demo()
    st.success("Seed complete.")
