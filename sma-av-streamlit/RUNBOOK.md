# **Agentic Ops - IPAV Workflow Orchestration — Runbook**

**Goal**  
Operate AV workflows Convert SOP's to Agentic workflows.  Create (Agents + Recipes + MCP Tools + Workflows) and observe results on a Dashboard, all inside the **IPAV** lifecycle: **Intake → Plan → Act → Verify**.

**Data & Persistence**  
- Primary DB (agents, recipes, workflows): your existing SQLAlchemy models.
- **Run telemetry** (runs, steps, artifacts): `core/runs_store.py` (SQLite file `avops.db` in app root).

---

## Navigation (actual app)

```
app
🏁 Setup Wizard
💬 Chat
🤖 Agents
📜 Recipes
🧰 MCP Tools
⚙️ Settings
🧩 Workflows
OO Dashboard
?? Help
🔎 Run Details
```

> Tip: Streamlit orders pages by file name, but this runbook references the **labels** you see in the sidebar.

---

## Architecture (logical)

```
[Pages] Setup Wizard / Settings / Chat / Agents / Recipes / MCP Tools / Workflows / Dashboard / Help / Run Details
   │
   ├──> [Controllers] core/workflow/engine.py + core/workflow/service.py
   │         └── executes recipes against agents; emits IPAV steps & artifacts
   │
   ├──> [RunStore] core/runs_store.py (SQLite)
   │         ├── WorkflowRun      (id, agent_id, recipe_id, trigger, status, duration, error, meta)
   │         ├── StepEvent        (phase: intake|plan|act|verify, payload, result)
   │         └── Artifact         (kind: kb|message|webinar|incident|file, url, external_id, data)
   │
   └──> [MCP Tools] (mock or real)  Slack / Zoom / ServiceNow / GitHub / Google Drive / Search
```

**IPAV**: consistent, observable checkpoints
- **Intake:** capture inputs/context
- **Plan:** preflight & validations
- **Act:** call tools/agents
- **Verify:** checks, metrics, artifacts (URLs/IDs) → **Dashboard**

---

## 🏁 Setup Wizard

**Purpose**  
- Initialize DB, seed sample agents/tools/recipes, and (optionally) create example workflows.
- Idempotent; safe to run multiple times.

**Steps**  
1. Click **Initialize** → creates tables, seed data (if not present).
2. (Optional) **Seed Examples** → demo agents/recipes, a sample workflow.
3. Verify in **Agents / Recipes / Workflows** pages.

**IPAV**  
- Intake: “seed on/off” choices  
- Plan: determine what’s missing  
- Act: create rows  
- Verify: toast + count summaries

---

## ⚙️ Settings

**Purpose**  
- Choose active LLM provider (OpenAI ↔ Anthropic) for Chat/SOP/Recipe generation.
- Toggle **Mock MCP** mode to avoid hitting external APIs.

**IPAV**  
- Intake: provider & keys  
- Plan: validate entries  
- Act: set session/env  
- Verify: indicator light + tool health passes

---

## 💬 Chat

**Purpose**  
- Turn natural language into SOPs/Recipes and quick agent runs.
- Exercise MCP tools via commands.

**Slash Commands**

- **SOP → Recipe draft**
  ```
  /sop agent=Support name="Projector Reset"
  Steps:
  - Gather room_id
  - Reset projector via Q-SYS
  - Verify image via Slack photo
  ```
  → Shows IPAV YAML draft; “Save Recipe” / “Attach to Agent”.

- **Recipe management**
  - `/recipe new "Projector Reset"`
  - `/recipe attach agent="Support" recipe="Projector Reset"`

- **Agent runs**
  - `/agent run "Support" recipe="Projector Reset"`

- **MCP diagnostics**
  - `/tool health calendar_scheduler`
  - `/tool action incident_ticketing '{"action":"create","args":{...}}'`

> **Quoting tip:** wrap multi-word names in double quotes. Key/value pairs accept `agent=`, `recipe=`, `name=`, etc., and JSON bodies should be quoted as shown above.

- **KB-Recipe Scout**
  ```
  /kb scout "zoom room hdmi black" allow=support.zoom.com,logitech.com
  ```
  → Search → synthesize KB HTML → create ServiceNow KB → save Recipe → Slack notify.

**IPAV**  
- Intake: user text + flags (JSON mode)  
- Plan: parse → validate  
- Act: attach/run; MCP actions  
- Verify: previews + artifacts → Dashboard run entry

---

## 🤖 Agents

**Purpose**  
- Define domain workers (support, events, builds, admin, monitoring).
- Select a recipe and **Trigger Run**.

**Steps**  
1. **Create Agent** (Name, Domain).  
2. Choose a **Recipe** from the dropdown.  
3. Click **Trigger Run**.  
4. Observe toast → check **Dashboard** for full run details.

**Typical Artifacts**  
- `kb` (ServiceNow sys_id + URL)  
- `message` (Slack channel URL)  
- `webinar` (Zoom id + join URL)

**IPAV**  
- Intake: recipe inputs (room_id/date/…)  
- Plan: preflight (creds/availability)  
- Act: call MCP tools  
- Verify: health checks + artifact URLs

---

## 📜 Recipes

**Purpose**
- Author YAML recipes with IPAV sections; validate, add guardrails, and version them.

**Best practices**
- Include `guardrails.timeout_minutes` and `guardrails.rollback_actions` for every recipe.
- Track `success_metrics` to surface KPIs on the dashboard.
- Commit YAML changes to Git (`git commit -am "recipe: add timeout"`) so teammates can review guardrails.

**Minimal scaffold**  
```yaml
name: Zoom Room Admin Policy Check
description: Validate room policy and report status.
version: 1
intake:
  - ask: "Room email or display name?"
plan:
  - action: "lookup_zoom_room"
    with: { query: "{{intake.room}}" }
act:
  - action: "check_policy"
  - action: "report_status"
verify:
  - check: "zoom_room.status == 'online'"
  - notify: "slack:#avops Room {{intake.room}} verified"
guardrails:
  - timeout_s: 20
  - rollback: "slack:#avops 'policy check failed; rollback initiated'"
```

**Best Practices**  
- Inputs in **intake**; preflight in **plan**; external effects in **act**; checks in **verify**.  
- Keep variables simple: `{{intake.room}}`.  
- Include **guardrails** (timeouts, rollback).  
- Version as `-v2.yaml` with a `changelog:`.

**Promotion Criteria**  
- Success ≥ **95%** (last 20 runs)  
- p95 duration ≤ **5s** (plan+act)  
- Verify pass ≥ **98%**  
- Risk/rollback documented

---

## 🧰 MCP Tools

**Purpose**
- Discover/check local tool connectors; call `/health` and `/action` (mock or real).
- Sample connectors ship with the app: `calendar_scheduler`, `incident_ticketing`, `qsys_control`, and `extron_control`.

**Health card snippet**  
```python
import requests, streamlit as st
def health_card(name, base):
    try:
        r = requests.get(f"{base}/health", timeout=3)
        ok = r.ok and r.json().get("ok", False)
        st.markdown(f"**{name}** {'🟢' if ok else '🔴'}")
        st.code(r.json(), language="json")
    except Exception as e:
        st.markdown(f"**{name}** 🔴"); st.caption(str(e))
```

**Action examples**  
- Slack post:
```json
{"tool":"slack","action":"post_message","args":{"channel":"#avops","text":"KB KB0012345 published"}}
```
- ServiceNow KB:
```json
{"tool":"servicenow","action":"create_kb","args":{"title":"Zoom HDMI Black","html":"<h2>Symptoms</h2>...","category":"AV","tags":["zoom","rooms"]}}
```
- Zoom webinar:
```json
{"tool":"zoom","action":"create_webinar","args":{"topic":"All Hands","start_time":"2025-10-21T17:00:00Z","duration":60}}
```

**IPAV**  
- Intake: action JSON  
- Plan: field checks  
- Act: vendor API call  
- Verify: ok + ids/URLs (store as artifacts)

---

## 🧩 Workflows

**Purpose**  
- Bind an **Agent** + **Recipe** + a **Trigger** (manual/interval).  
- Status dot summarizes the latest outcome.

**Steps**  
1. Name the workflow (e.g., `Event Intake`).  
2. Select Agent and Recipe.  
3. Choose Trigger: **manual** or **interval (minutes)**.  
4. **Create Workflow**.  
5. Click **Run now** or use **Tick scheduler**.  
6. Inspect run details in **Dashboard**.

**IPAV**  
- Intake: configuration (Agent/Recipe/Trigger)  
- Plan: scheduler decides due runs  
- Act: engine executes  
- Verify: status dot + run artifacts

---

## Dashboard

**Purpose**  
- System-wide observability of runs, KPIs, and artifacts.

**Widgets**  
- **KPIs**: total runs, success rate, p95 duration, last error  
- **Recent runs**: id, name, status, trigger, agent, recipe, duration, started_at  
- **Trend**: runs/hour (or per day)  
- **Details**:  
  - Steps: Intake → Plan → Act → Verify (payload/result)  
  - Artifacts: KB sys_id+URL, Slack message URL, Zoom webinar id, etc.

> If you filtered by time or status, ensure `RunStore.latest_runs(limit=..., status=[...], since=...)` is used server-side.

---

## IPAV Swimlanes (examples)

### KB-Recipe Scout (Events Agent)
```
Intake:  seed query, allowed domains
Plan:    search N pages; extract steps; draft KB HTML + Recipe YAML
Act:     create ServiceNow KB; save Recipe; Slack notify with links
Verify:  SN returns sys_id; Slack 200 OK; artifacts stored
```

### Zoom Room — HDMI Black
```
Intake:  ask room email/display name
Plan:    validate room; preflight Zoom API
Act:     run policy/self-heal; update incident/story
Verify:  zoom room status OK; Slack confirmation; artifacts logged
```

### Event Intake Wizard → Artifacts
```
Intake:  type/date/POC/options
Plan:    expand to schema; create SN Story & subtasks
Act:     create Zoom webinar; post Slack confirmation
Verify:  pre-event checks; rehearsal status; artifact links saved
```

---

## Troubleshooting

- **Runs not visible:** Ensure run code is wrapped with `RunStore.workflow_run(...)` and steps/artifacts are logged.  
- **Model toggle doesn’t change:** Confirm `st.session_state["llm_provider"]` is set in **Settings**; check sidebar indicator.  
- **MCP failures/timeouts:** Toggle **Mock MCP Tools** in Settings; confirm `/health` before `/action`.  
- **Recipe schema errors:** Keep IPAV sections (`intake/plan/act/verify`) and keys simple; validate in editor.

---

## Appendix: Provider Helper

```python
# core/llm_provider.py
import os
def pick_model(session_state) -> str:
    p = (session_state.get("llm_provider") or "OpenAI").lower()
    return "claude-3-5-sonnet-latest" if p == "anthropic" else "gpt-4o-mini"
```

---

**End of Runbook**
