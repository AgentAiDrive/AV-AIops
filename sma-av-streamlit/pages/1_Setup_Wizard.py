import streamlit as st
import streamlit.components.v1 as components
from core.db.seed import seed_demo
from core.ui.page_tips import show as show_tip

PAGE_KEY = "Setup Wizard"
show_tip(PAGE_KEY)

st.title("🏁 Setup Wizard")
st.write("Initialize database, seed demo agents, tools, and recipes.")

if st.button("Initialize database & seed demo data"):
    seed_demo()
    st.success("Seed complete.")

# ⬇️ Add this caption block (summary + how-to-complete)
st.caption("""
**What this form is for:** Capture your AV environment’s meeting volume, costs, support incidents, hours of operation, 
and license inventory so the app can auto-generate an **SOP JSON** and an **IPAV Recipe YAML** for a “Baseline Capture” workflow.

**How to complete the form:**
1. Choose the **input mode** for Meetings and Support Incidents, then enter your numbers.
2. Fill **Average attendees per meeting** and **Loaded cost per hour**.
3. Select **Hours of Operation** (or provide a **Custom** string).
4. Under **License Optimization**, tick platforms you own and enter **license counts** (optional: cost & underuse % for savings preview).
5. Click **Generate** to preview, then use **Download/Copy** for SOP JSON and IPAV Recipe YAML.
""")

st.divider()
st.header("📊 Value Intake → SOP JSON → IPAV Recipe YAML")

# ... keep your existing `form_html = """..."""` and
#     components.html(form_html, height=2100, scrolling=True) below ...
