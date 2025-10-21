import json
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

# ✅ your imports
from core.db.seed import seed_demo
from core.ui.page_tips import show as show_tip

# ---- Page header / tip ----
PAGE_KEY = "Setup Wizard"
show_tip(PAGE_KEY)

st.title("🏁 Setup Wizard")
st.write("Initialize database, seed demo agents, tools, and recipes.")

if st.button("Initialize database & seed demo data"):
    seed_demo()
    st.success("Seed complete.")

st.divider()
st.header("📊 Value Intake → SOP JSON → IPAV Recipe YAML")

st.caption(
    "**What this form is for:** Capture your AV environment’s meeting volume, costs, "
    "support incidents, hours of operation, and license inventory so the app can auto-generate "
    "an **SOP JSON** and an **IPAV Recipe YAML** for a “Baseline Capture” workflow.\n\n"
    "**How to complete the form:**\n"
    "1) Choose the **input mode** for Meetings and Support Incidents, then enter your numbers.\n"
    "2) Fill **Average attendees per meeting** and **Loaded cost per hour**.\n"
    "3) Select **Hours of Operation** (or provide a **Custom** string).\n"
    "4) Under **License Optimization**, tick platforms you own and enter **license counts** "
    "(optional: cost & underuse % for savings preview).\n"
    "5) Click **Generate** to preview, then use **Copy** or **Download** for SOP JSON and IPAV Recipe YAML."
)

# ---------- helpers ----------
DEFAULT_PLATFORMS = [
    {"key": "zoom_meetings", "label": "Zoom Meetings"},
    {"key": "zoom_rooms", "label": "Zoom Rooms"},
    {"key": "zoom_webinar", "label": "Zoom Webinar"},
    {"key": "zoom_phone", "label": "Zoom Phone"},
    {"key": "microsoft_teams", "label": "Microsoft Teams (E/M add-ons)"},
    {"key": "webex_meetings", "label": "Webex Meetings"},
    {"key": "webex_calling", "label": "Webex Calling"},
    {"key": "google_meet", "label": "Google Meet add-ons"},
]

def yaml_escape(s: str) -> str:
    return (s or "").replace('"', '\\"')

def build_sop(payload: dict) -> dict:
    now = datetime.utcnow().isoformat()
    steps = [
        {
            "id": "prep_intake_payload",
            "title": "Confirm intake payload",
            "instruction": "Review captured parameters and confirm scope (rooms, employees, hours, incidents).",
            "inputs": payload,
            "expected_output": "Signed-off intake payload for baseline run.",
        },
        {
            "id": "mcp_scaffold",
            "title": "Create/verify MCP connections",
            "instruction": "Ensure MCP tool configs exist and are reachable.",
            "tools": [
                {"id": "mcp.zoom", "secrets": ["ZOOM_ACCOUNT_ID", "ZOOM_CLIENT_ID", "ZOOM_CLIENT_SECRET"]},
                {"id": "mcp.zoom_workspaces", "secrets": ["ZOOM_WORKSPACES_API_KEY"]},
                {"id": "mcp.servicenow", "secrets": ["SN_INSTANCE", "SN_USERNAME", "SN_TOKEN"]},
                {"id": "mcp.25live", "secrets": ["TWENTYFIVELIVE_BASE_URL", "TWENTYFIVELIVE_API_KEY"]},
            ],
            "expected_output": "All MCP tools registered and authenticated.",
        },
        {
            "id": "baseline_capture",
            "title": "Capture baseline metrics",
            "instruction": "Using MCP tools, pull 30-day baseline: meetings, participants, minutes, room utilization, incident rates, and license utilization.",
            "expected_output": "Baseline snapshot persisted with evidence (timestamps, queries, counts).",
        },
        {
            "id": "kb_seed",
            "title": "Seed/Update KB in ServiceNow",
            "instruction": "Synthesize an executive-readable baseline summary and post to ServiceNow KB; notify Slack.",
            "expected_output": "SN KB article link + Slack message URL.",
        },
        {
            "id": "schedule_runs",
            "title": "Schedule recurring baseline rollups",
            "instruction": "Set weekly automation to refresh metrics and track Value Realized deltas.",
            "expected_output": "Scheduled workflow entry visible on Dashboard.",
        },
    ]
    return {
        "sop_title": "IPAV Baseline Capture + MCP Scaffold",
        "goal": "Establish 30-day baseline and license underuse, then schedule deltas for Value Realized.",
        "context": payload,
        "steps": steps,
        "acceptance_criteria": [
            "MCP tools registered and authenticated.",
            "Baseline snapshot saved with evidence hashes and timestamps.",
            "KB article created/updated with links to evidence and charts.",
            "Slack notification posted to #av-ops (or configured channel).",
        ],
        "how_to_implement": [
            "Click “Download SOP JSON” and paste into Chat with /sop.",
            "Review generated Recipe YAML, save it in Recipes.",
            "Attach the recipe to an agent in Agents.",
            "Create a Workflow “Baseline Capture” using that recipe and run it.",
            "View evidence and deltas in Dashboard; schedule weekly runs.",
        ],
        "meta": {"generated_at": now, "schema_version": "1.0.0"},
    }

def build_yaml(payload: dict) -> str:
    hours = payload.get("hours_of_operation") or "hours"
    platforms = payload.get("license_optimization", {}).get("selected", [])
    mv = payload.get("meeting_volume", {}) or {}
    inc = payload.get("support_incidents", {}) or {}

    plat_yaml = []
    for p in platforms:
        plat_yaml.append(
            f'      - key: {p.get("key")}\n'
            f'        label: "{yaml_escape(p.get("label",""))}"\n'
            f'        licenses: {p.get("licenses", 0)}\n'
            f'        monthly_cost_per_license_usd: {p.get("monthly_cost_per_license_usd") or 0}\n'
            f'        underuse_percent: {p.get("underuse_percent") or 0}'
        )
    plat_block = "\n".join(plat_yaml) if plat_yaml else "      - {}"

    stacks = payload.get("environment_defaults", {}).get("stacks", ["Zoom","Q-SYS","Crestron","Logitech"])
    stacks_str = ", ".join(f'"{yaml_escape(s)}"' for s in stacks)

    return f'''# IPAV Recipe: Baseline Capture + MCP Scaffold
version: "1.0"
recipe:
  id: ipav-baseline-{hours.replace(" ", "-").lower()}
  name: "IPAV Baseline Capture"
  description: >
    Establishes baseline meeting volume, attendance, incident rates, and license utilization.
    Scaffolds MCP tools (Zoom, Zoom Workspaces, ServiceNow, 25Live) and persists a baseline snapshot
    for Value Realized tracking.
  tags: [baseline, value-realized, intake, mcp, ipav]
  parameters:
    avg_attendees_per_meeting: {payload.get("avg_attendees_per_meeting") or 0}
    loaded_cost_per_hour_usd: {payload.get("loaded_cost_per_hour_usd") or 0}
    hours_of_operation: "{yaml_escape(payload.get("hours_of_operation",""))}"
    environment:
      rooms: {payload.get("environment_defaults",{}).get("rooms", 500)}
      employees: {payload.get("environment_defaults",{}).get("employees", 10000)}
      stacks: [{stacks_str}]
    meeting_volume:
      mode: {mv.get("mode","per_room_per_day")}
      avg_meetings_per_room_per_day: {mv.get("avg_meetings_per_room_per_day") or 0}
      rooms_count: {mv.get("rooms_count") or 0}
      meetings_enterprise_per_month: {mv.get("meetings_enterprise_per_month") or 0}
      employees_count: {mv.get("employees_count") or 0}
    support_incidents:
      mode: {inc.get("mode","per_room")}
      incidents_per_room_per_month: {inc.get("incidents_per_room_per_month") or 0}
      rooms_count: {inc.get("rooms_count") or 0}
      incidents_enterprise_per_month: {inc.get("incidents_enterprise_per_month") or 0}
    license_candidates:
{plat_block}
  prerequisites:
    mcp_tools:
      - id: mcp.zoom
        secrets: [ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET]
      - id: mcp.zoom_workspaces
        secrets: [ZOOM_WORKSPACES_API_KEY]
      - id: mcp.servicenow
        secrets: [SN_INSTANCE, SN_USERNAME, SN_TOKEN]
      - id: mcp.25live
        secrets: [TWENTYFIVELIVE_BASE_URL, TWENTYFIVELIVE_API_KEY]

  flow:
    - id: ensure_mcp
      action: ensure_mcp_tools
      input:
        tools: ["mcp.zoom", "mcp.zoom_workspaces", "mcp.servicenow", "mcp.25live"]

    - id: fetch_zoom_baseline
      action: call
      tool: mcp.zoom.reports
      input:
        date_range: "last_30_days"
        metrics: ["meetings_count","participants_total","meeting_minutes"]
      save_as: zoom_baseline

    - id: fetch_workspaces_util
      action: call
      tool: mcp.zoom_workspaces.utilization
      input:
        rooms: ${{params.environment.rooms}}
      save_as: workspaces_util

    - id: compute_incident_baseline
      action: compute
      input:
        mode: ${{params.support_incidents.mode}}
        incidents_per_room_per_month: ${{params.support_incidents.incidents_per_room_per_month}}
        rooms_count: ${{params.support_incidents.rooms_count}}
        incidents_enterprise_per_month: ${{params.support_incidents.incidents_enterprise_per_month}}
      save_as: incidents_baseline

    - id: compute_license_underuse
      action: compute_license_savings
      input:
        candidates: ${{params.license_candidates}}
      save_as: license_baseline

    - id: persist_snapshot
      action: persist_baseline
      input:
        snapshot:
          zoom: ${{steps.fetch_zoom_baseline.output}}
          workspaces: ${{steps.fetch_workspaces_util.output}}
          incidents: ${{steps.compute_incident_baseline.output}}
          licenses: ${{steps.compute_license_underuse.output}}
      save_as: baseline_snapshot

    - id: publish_kb
      action: call
      tool: mcp.servicenow.kb.create_or_update
      input:
        title: "IPAV Baseline Snapshot"
        body_markdown: |
          ## Baseline Snapshot
          Generated: ${{now}}
          ### Zoom
          ${{steps.fetch_zoom_baseline.output}}
          ### Workspaces
          ${{steps.fetch_workspaces_util.output}}
          ### Incidents
          ${{steps.compute_incident_baseline.output}}
          ### Licenses
          ${{steps.compute_license_underuse.output}}
      save_as: kb_article

    - id: notify_slack
      action: call
      tool: mcp.servicenow.notify_slack
      input:
        channel: "#av-ops"
        text: "Baseline snapshot ready — KB: ${{steps.publish_kb.output.url}}"

  success_criteria:
    - "All MCP tools reachable and authenticated."
    - "Baseline snapshot stored with evidence references."
    - "ServiceNow KB updated with summary and links."
    - "Slack notification sent to the configured channel."

  outputs:
    - id: baseline_snapshot
      from: baseline_snapshot
    - id: kb_article_url
      from: publish_kb
'''

def validate(payload: dict):
    errors, warns = [], []
    mv = payload.get("meeting_volume", {}) or {}
    if mv.get("mode") == "per_room_per_day":
        per_day = mv.get("avg_meetings_per_room_per_day")
        if per_day is None or per_day < 0 or per_day > 24:
            errors.append("Avg meetings per room per day must be between 0 and 24.")
        if not mv.get("rooms_count") or mv["rooms_count"] <= 0:
            errors.append("Rooms count must be a positive number.")
    else:
        mpm = mv.get("meetings_enterprise_per_month")
        if mpm is None or mpm < 0:
            errors.append("Enterprise meetings per month must be non-negative.")
        if not mv.get("employees_count") or mv["employees_count"] <= 0:
            errors.append("Employees count must be a positive number.")

    att = payload.get("avg_attendees_per_meeting")
    if att is None or att <= 0:
        errors.append("Average attendee count per meeting must be greater than 0.")

    cost = payload.get("loaded_cost_per_hour_usd")
    if cost is None or cost < 0:
        errors.append("Loaded cost per hour must be 0 or greater.")

    inc = payload.get("support_incidents", {}) or {}
    if inc.get("mode") == "per_room":
        ipm = inc.get("incidents_per_room_per_month")
        if ipm is None or ipm < 0:
            errors.append("Incidents per room per month must be non-negative.")
        if not inc.get("rooms_count") or inc["rooms_count"] <= 0:
            errors.append("Rooms count for incidents must be positive.")
    else:
        iepm = inc.get("incidents_enterprise_per_month")
        if iepm is None or iepm < 0:
            errors.append("Incidents per month must be non-negative.")

    for p in payload.get("license_optimization", {}).get("selected", []):
        if p.get("licenses") and p["licenses"] <= 0:
            errors.append(f'{p.get("label")}: license count must be greater than 0.')
        up = p.get("underuse_percent")
        if up is not None and (up < 0 or up > 100):
            errors.append(f'{p.get("label")}: underuse % must be between 0 and 100.')
        if up and up > 25:
            warns.append(f'{p.get("label")}: underuse > 25%; consider reducing licenses.')
    return errors, warns

# ---------- form ----------
with st.form("intake"):
    st.subheader("Meeting Volume")
    meet_mode = st.radio(
        "Average meetings input mode",
        ["per_room_per_day", "enterprise_per_month"],
        format_func=lambda v: "Per room • per day" if v == "per_room_per_day" else "Enterprise • per month",
        horizontal=True,
    )

    c1, c2 = st.columns(2)
    if meet_mode == "per_room_per_day":
        avg_mtgs = c1.number_input("Avg meetings / room / day", min_value=0.0, max_value=24.0, step=0.1, value=5.0)
        rooms_count = c2.number_input("Rooms in scope", min_value=1, step=1, value=500)
        mv_payload = {
            "mode": meet_mode,
            "avg_meetings_per_room_per_day": avg_mtgs,
            "rooms_count": rooms_count,
        }
    else:
        total_mtgs = c1.number_input("Total meetings / month (enterprise)", min_value=0, step=100, value=80000)
        employees = c2.number_input("Employees in scope", min_value=1, step=100, value=10000)
        mv_payload = {
            "mode": meet_mode,
            "meetings_enterprise_per_month": total_mtgs,
            "employees_count": employees,
        }

    c3, c4 = st.columns(2)
    avg_attendees = c3.number_input("Average attendee count per meeting", min_value=1, step=1, value=6)
    loaded_cost = c4.number_input("Average loaded cost per hour per employee (USD)", min_value=0, step=1, value=85)

    st.subheader("Support Incidents")
    inc_mode = st.radio(
        "Incidents input mode",
        ["per_room", "enterprise"],
        format_func=lambda v: "Per room • per month" if v == "per_room" else "Enterprise • per month",
        horizontal=True,
    )

    if inc_mode == "per_room":
        d1, d2 = st.columns(2)
        inc_per_room = d1.number_input("Estimated incidents / room / month", min_value=0.0, step=0.1, value=0.3)
        rooms_count_inc = d2.number_input("Rooms in scope (incidents)", min_value=1, step=1, value=500)
        inc_payload = {
            "mode": inc_mode,
            "incidents_per_room_per_month": inc_per_room,
            "rooms_count": rooms_count_inc,
        }
    else:
        d1, d2 = st.columns(2)
        inc_ent = d1.number_input("Estimated incidents / month (enterprise)", min_value=0, step=1, value=150)
        rooms_ref = d2.number_input("Rooms in scope (reference)", min_value=1, step=1, value=500)
        inc_payload = {
            "mode": inc_mode,
            "incidents_enterprise_per_month": inc_ent,
            "rooms_count_reference": rooms_ref,
        }

    st.subheader("Hours of Operation")
    hours_choice = st.radio("Select one", ["9-5 weekdays", "7-7 weekdays", "24x5", "24x7", "custom"], horizontal=True)
    hours_custom = ""
    if hours_choice == "custom":
        hours_custom = st.text_input("Custom hours (e.g., 6–8 (Mon–Sat))", value="")
    hours_value = hours_custom if hours_choice == "custom" else hours_choice

    st.subheader("License Optimization Candidates")
    sel = []
    with st.expander("Add / edit platforms"):
        for plat in DEFAULT_PLATFORMS:
            on = st.checkbox(plat["label"], key=f"plat_{plat['key']}")
            if on:
                q1, q2, q3 = st.columns(3)
                qty = q1.number_input(f"Licenses — {plat['label']}", min_value=0, step=1, value=0, key=f"qty_{plat['key']}")
                cost = q2.number_input(
                    f"Monthly $ / license — {plat['label']}", min_value=0.0, step=1.0, value=0.0, key=f"cost_{plat['key']}"
                )
                under = q3.number_input(
                    f"Underuse % — {plat['label']}", min_value=0, max_value=100, step=1, value=0, key=f"under_{plat['key']}"
                )
                sel.append(
                    {
                        "key": plat["key"],
                        "label": plat["label"],
                        "licenses": int(qty),
                        "monthly_cost_per_license_usd": float(cost) if cost else None,
                        "underuse_percent": int(under) if under else None,
                    }
                )

    est_savings = sum(
        (p.get("licenses") or 0)
        * (p.get("monthly_cost_per_license_usd") or 0)
        * ((p.get("underuse_percent") or 0) / 100.0)
        for p in sel
    )
    st.info(f"Est. reclaimable (monthly): **${est_savings:,.0f}**")

    submitted = st.form_submit_button("Generate (Preview JSON & YAML)")

# ---------- build / validate / preview ----------
if submitted:
    payload = {
        "meeting_volume": mv_payload,
        "avg_attendees_per_meeting": int(avg_attendees),
        "loaded_cost_per_hour_usd": int(loaded_cost),
        "support_incidents": inc_payload,
        "hours_of_operation": hours_value,
        "license_optimization": {"selected": sel, "est_monthly_savings": est_savings},
        "environment_defaults": {"rooms": 500, "employees": 10000, "stacks": ["Zoom", "Q-SYS", "Crestron", "Logitech"]},
        "meta": {"generated_at": datetime.utcnow().isoformat(), "schema_version": "1.0.0"},
    }

    # validate
    errors, warns = validate(payload)
    if errors:
        st.error("• " + "\n• ".join(errors))
    if warns:
        st.warning("• " + "\n• ".join(warns))

    # preview + actions
    if not errors:
        sop = build_sop(payload)
        yaml_txt = build_yaml(payload)
        json_txt = json.dumps(sop, indent=2)

        t1, t2 = st.tabs(["SOP JSON", "IPAV Recipe YAML"])

        with t1:
            st.code(json_txt, language="json")
            st.download_button("Download SOP JSON", json_txt, file_name="ipav_baseline_sop.json", mime="application/json")
            components.html(
                f"""
                <button onclick='navigator.clipboard.writeText({json.dumps(json_txt)}).then(()=>{{this.innerText="Copied ✓"; setTimeout(()=>this.innerText="Copy JSON",1500)}})'>
                  Copy JSON
                </button>
                """,
                height=40,
            )

        with t2:
            st.code(yaml_txt, language="yaml")
            st.download_button(
                "Download IPAV Recipe YAML", yaml_txt, file_name="ipav_baseline_recipe.yaml", mime="text/yaml"
            )
            components.html(
                f"""
                <button onclick='navigator.clipboard.writeText({json.dumps(yaml_txt)}).then(()=>{{this.innerText="Copied ✓"; setTimeout(()=>this.innerText="Copy YAML",1500)}})'>
                  Copy YAML
                </button>
                """,
                height=40,
            )
