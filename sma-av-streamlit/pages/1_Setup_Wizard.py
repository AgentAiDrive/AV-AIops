import streamlit as st
import streamlit.components.v1 as components
from core.db.seed import seed_demo
from core.ui.page_tips import show as show_tip

PAGE_KEY = "Setup Wizard"
show_tip(PAGE_KEY)

# Title and description for the setup wizard
st.title("🏁 Setup Wizard")
st.write("Initialize database, seed demo agents, tools, and recipes.")

# Button to seed demo data
if st.button("Initialize database & seed demo data"):
    seed_demo()
    st.success("Seed complete.")

# Instructions for using the form
st.caption("""
**What this form is for:** Capture your AV environment’s meeting volume, costs, support incidents, hours of operation, \
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

# HTML intake form for capturing environment details.  The form uses inline
# JavaScript to manage UI toggles, compute savings, build payloads, and
# generate the SOP JSON and YAML outputs.  At the bottom of the script we
# insert a validation function and modify the submit handler to perform
# validation before generating the outputs.
form_html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>AV Ops Value Intake</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root{
      --bg:#0b0c10; --panel:#111318; --muted:#98a2b3; --border:#1f242d;
      --text:#e6eaf2; --accent:#66d9e8; --good:#22c55e; --warn:#f59e0b; --shadow:0 10px 25px rgba(0,0,0,.35); --radius:16px;
    }
    *{box-sizing:border-box}
    body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial;background:radial-gradient(1200px 800px at 20% -10%, #1b2333 0%, #0b0c10 55%) fixed;color:var(--text);line-height:1.45;}
    .wrap{max-width:1080px;margin:8px auto 24px;padding:0 16px;}
    .title{display:flex;align-items:center;gap:14px;margin:0 0 12px 0;font-weight:800;letter-spacing:.2px;}
    .title .pill{font-size:12px;color:#0b0c10;background:var(--accent);border-radius:999px;padding:4px 10px;font-weight:700;}
    .card{background:linear-gradient(180deg,rgba(255,255,255,.03),rgba(255,255,255,.01));border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);padding:22px;}
    .grid{display:grid;gap:16px}
    @media (min-width:820px){ .grid.two{grid-template-columns:1fr 1fr} .grid.three{grid-template-columns:1fr 1fr 1fr} }
    h2{font-size:18px;margin:12px 0 6px 0}
    fieldset{border:1px dashed var(--border);border-radius:12px;padding:14px;margin:0}
    legend{padding:0 8px;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.12em}
    label{display:block;font-size:14px;margin-bottom:6px}
    .row{display:grid;gap:8px}
    .hint{color:var(--muted);font-size:12px}
    input[type="number"], input[type="text"], select{width:100%;background:#0c111b;border:1px solid var(--border);color:var(--text);border-radius:10px;padding:10px 12px;outline:none;}
    input[type="number"]:focus, input[type="text"]:focus, select:focus{border-color:var(--accent)}
    .seg{display:flex;background:#0c111b;border:1px solid var(--border);border-radius:10px;overflow:hidden}
    .seg input{display:none}
    .seg label{flex:1;text-align:center;padding:10px;cursor:pointer;font-size:14px;border-right:1px solid var(--border);}
    .seg label:last-child{border-right:none}
    .seg input:checked + label{background:linear-gradient(180deg,#102235,#0c111b);color:var(--accent);font-weight:700}
    .inline{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
    .checkbox-row{display:grid;grid-template-columns:auto 1fr;gap:8px;align-items:start;padding:10px;border:1px solid var(--border);border-radius:10px;background:#0c111b;}
    .mini-grid{display:grid;gap:8px}
    @media (min-width:720px){ .mini-grid{grid-template-columns:repeat(3, minmax(0,1fr));} }
    .totals{display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;font-size:13px;color:var(--muted)}
    .pill-num{background:#121826;border:1px solid var(--border);padding:6px 10px;border-radius:999px}
    .btns{display:flex;gap:10px;flex-wrap:wrap}
    button{border:1px solid var(--border);background:#121826;color:var(--text);border-radius:12px;padding:10px 14px;font-weight:700;cursor:pointer;}
    button.primary{background:linear-gradient(180deg,#1a2a40,#111a29);border-color:#1b2a42}
    button.primary:hover{border-color:var(--accent);box-shadow:0 0 0 2px rgba(102,217,232,.15) inset}
    .success{color:var(--good)} .warn{color:var(--warn)}
    .out{margin-top:18px;background:#0c111b;border:1px solid var(--border);border-radius:12px;padding:12px}
    textarea{width:100%;min-height:160px;background:transparent;border:none;color:var(--text);resize:vertical;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;}
    .small{font-size:12px;color:var(--muted)}
    details{background:#0c111b;border:1px solid var(--border);border-radius:12px;padding:12px}
    summary{cursor:pointer;font-weight:700;margin-bottom:8px}
  </style>
</head>
<body>
  <div class="wrap">
    <h1 class="title"><span class="pill">Intake</span> AV Ops Value & License Optimization — Data Capture</h1>
    <p class="hint" style="margin:0 0 20px 0;">Provide typical ranges; estimates are fine. Then export as SOP JSON and/or IPAV Recipe YAML.</p>

    <form id="intake" class="grid" novalidate>
      <!-- MEETING VOLUME -->
      <div class="card">
        <h2>Meeting Volume</h2>
        <div class="row">
          <fieldset>
            <legend>Average meetings input mode</legend>
            <div class="seg" role="tablist" aria-label="Meetings input mode">
              <input type="radio" id="mode_room_day" name="meet_mode" value="per_room_per_day" checked>
              <label for="mode_room_day">Per room • per day</label>
              <input type="radio" id="mode_ent_month" name="meet_mode" value="enterprise_per_month">
              <label for="mode_ent_month">Enterprise • per month</label>
            </div>
            <div id="perRoom" class="grid two" style="margin-top:12px;">
              <div>
                <label for="mtgs_per_room_day">Avg meetings / room / day</label>
                <input id="mtgs_per_room_day" type="number" min="0" step="0.1" placeholder="e.g., 5.0" inputmode="decimal">
                <div class="hint">If uncertain, 3–8 is common depending on culture & space type.</div>
              </div>
              <div>
                <label for="rooms_count">Rooms in scope</label>
                <input id="rooms_count" type="number" min="0" step="1" placeholder="e.g., 500" inputmode="numeric" value="500">
                <div class="hint">Your example environment uses 500 rooms; adjust if needed.</div>
              </div>
            </div>
            <div id="enterpriseMonthly" class="grid two" style="display:none;margin-top:12px;">
              <div>
                <label for="mtgs_enterprise_month">Total meetings / month (enterprise)</label>
                <input id="mtgs_enterprise_month" type="number" min="0" step="1" placeholder="e.g., 80000" inputmode="numeric">
              </div>
              <div>
                <label for="employees_count">Employees in scope</label>
                <input id="employees_count" type="number" min="0" step="1" placeholder="e.g., 10000" inputmode="numeric" value="10000">
              </div>
            </div>
          </fieldset>

          <div class="grid two" style="margin-top:12px;">
            <div>
              <label for="avg_attendees">Average attendee count per meeting</label>
              <input id="avg_attendees" type="number" min="1" step="1" placeholder="e.g., 6" inputmode="numeric">
            </div>
            <div>
              <label for="loaded_cost_hour">Average loaded cost per hour per employee (USD)</label>
              <input id="loaded_cost_hour" type="number" min="0" step="1" placeholder="e.g., 85" inputmode="decimal">
              <div class="hint">Fully-loaded: salary + benefits + overhead (estimate is fine).</div>
            </div>
          </div>
        </div>
      </div>

      <!-- SUPPORT INCIDENTS -->
      <div class="card">
        <h2>Support Incidents</h2>
        <fieldset class="row">
          <legend>Incidents input mode</legend>
          <div class="seg" role="tablist" aria-label="Incidents input mode">
            <input type="radio" id="inc_mode_room" name="inc_mode" value="per_room" checked>
            <label for="inc_mode_room">Per room • per month</label>
            <input type="radio" id="inc_mode_ent" name="inc_mode" value="enterprise">
            <label for="inc_mode_ent">Enterprise • per month</label>
          </div>

          <div id="incPerRoom" class="grid two" style="margin-top:12px;">
            <div>
              <label for="incidents_per_room_month">Estimated incidents / room / month</label>
              <input id="incidents_per_room_month" type="number" min="0" step="0.1" placeholder="e.g., 0.3" inputmode="decimal">
            </div>
            <div>
              <label for="rooms_count_inc">Rooms in scope</label>
              <input id="rooms_count_inc" type="number" min="0" step="1" placeholder="e.g., 500" inputmode="numeric" value="500">
            </div>
          </div>

          <div id="incEnterprise" class="grid two" style="display:none;margin-top:12px;">
            <div>
              <label for="incidents_enterprise_month">Estimated incidents / month (enterprise)</label>
              <input id="incidents_enterprise_month" type="number" min="0" step="1" placeholder="e.g., 150" inputmode="numeric">
            </div>
            <div>
              <label for="rooms_count_inc_ro">Rooms in scope</label>
              <input id="rooms_count_inc_ro" type="number" min="0" step="1" placeholder="e.g., 500" inputmode="numeric" value="500">
            </div>
          </div>
        </fieldset>
      </div>

      <!-- HOURS OF OPERATION -->
      <div class="card">
        <h2>Hours of Operation</h2>
        <fieldset>
          <legend>Select one</legend>
          <div class="inline" role="radiogroup" aria-label="Hours of operation">
            <label><input type="radio" name="hours" value="9-5 weekdays" checked> 9–5 (Weekdays)</label>
            <label><input type="radio" name="hours" value="7-7 weekdays"> 7–7 (Weekdays)</label>
            <label><input type="radio" name="hours" value="24x5"> 24×5 (Mon–Fri)</label>
            <label><input type="radio" name="hours" value="24x7"> 24×7</label>
            <label class="inline">
              <input type="radio" name="hours" value="custom" id="hours_custom_radio"> Custom
              <input type="text" id="hours_custom" placeholder="e.g., 6–8 (Mon–Sat)" style="display:none;max-width:260px">
            </label>
          </div>
          <div class="hint" style="margin-top:8px;">Choose the closest fit; you can describe specifics via “Custom”.</div>
        </fieldset>
      </div>

      <!-- LICENSE OPTIMIZATION -->
      <div class="card">
        <h2>License Optimization Candidates</h2>
        <p class="hint" style="margin-top:-4px">Check platforms and (optionally) cost & underuse % for savings preview.</p>
        <div id="platforms" class="grid" style="margin-top:10px;"></div>
        <div class="btns" style="margin-top:10px;">
          <button type="button" id="addPlatform">+ Add custom platform</button>
        </div>
        <div class="totals">
          <span class="pill-num" id="selPlatforms">0 platforms selected</span>
          <span class="pill-num">Est. reclaimable (monthly): <strong id="savingsPreview">$0</strong></span>
          <span class="small">Savings = Σ (licenses × cost × underuse%)</span>
        </div>
      </div>

      <!-- IMPLEMENTATION HOW-TO (shown in SOP too) -->
      <div class="card">
        <h2>How to Implement in the IPAV App</h2>
        <details open>
          <summary>Step-by-step</summary>
          <ol class="hint">
            <li>Click <strong>Generate</strong> → <strong>Download SOP JSON</strong>.</li>
            <li>Open <em>Chat</em> in the Streamlit app and paste the JSON with <code>/sop</code>.</li>
            <li>Review the generated <strong>Recipe YAML</strong>, then save it in <em>Recipes</em>.</li>
            <li>Attach the recipe to an agent in <em>Agents</em>.</li>
            <li>Create a <em>Workflow</em> “Baseline Capture” using that agent + recipe; run it.</li>
            <li>Verify evidence and metrics in <em>Dashboard</em> and schedule periodic runs.</li>
          </ol>
        </details>
      </div>

      <!-- ACTIONS -->
      <div class="card">
        <h2>Finish</h2>
        <div class="btns" style="margin-bottom:10px;">
          <button type="button" id="loadSample">Load sample values (500 rooms / 10k employees)</button>
          <button type="submit" class="primary">Generate (Preview JSON & YAML)</button>
          <button type="button" id="copyJson">Copy JSON</button>
          <button type="button" id="downloadSop">Download SOP JSON</button>
          <button type="button" id="copyYaml">Copy YAML</button>
          <button type="button" id="downloadYaml">Download IPAV Recipe YAML</button>
          <span id="copyState" class="small"></span>
        </div>
        <div class="out"><textarea id="jsonOut" placeholder="// SOP JSON preview…" readonly></textarea></div>
        <div class="out"><textarea id="yamlOut" placeholder="# IPAV Recipe YAML preview…" readonly></textarea></div>
        <div class="small">Tip: Paste SOP JSON into Chat with <code>/sop</code> to regenerate the YAML in-app, or import the YAML directly.</div>
      </div>
    </form>
  </div>

  <script>
    const $ = (sel, root=document)=>root.querySelector(sel);
    const $$ = (sel, root=document)=>Array.from(root.querySelectorAll(sel));
    const money = n => isFinite(n) ? n.toLocaleString(undefined,{style:'currency',currency:'USD',maximumFractionDigits:0}) : '$0';

    // --- toggles
    const modeRadios = $$('input[name="meet_mode"]');
    const perRoom = $('#perRoom'); const entMonthly = $('#enterpriseMonthly');
    modeRadios.forEach(r=>r.addEventListener('change',()=>{
      const room = $('input[name="meet_mode"]:checked').value === 'per_room_per_day';
      perRoom.style.display = room ? '' : 'none';
      entMonthly.style.display = room ? 'none' : '';
    }));
    const incModeRadios = $$('input[name="inc_mode"]');
    const incPerRoom = $('#incPerRoom'); const incEnterprise = $('#incEnterprise');
    incModeRadios.forEach(r=>r.addEventListener('change',()=>{
      const room = $('input[name="inc_mode"]:checked').value === 'per_room';
      incPerRoom.style.display = room ? '' : 'none';
      incEnterprise.style.display = room ? 'none' : '';
    }));
    const hoursCustomRadio = $('#hours_custom_radio');
    const hoursCustom = $('#hours_custom');
    $$('input[name="hours"]').forEach(r=>{
      r.addEventListener('change',()=>{ hoursCustom.style.display = hoursCustomRadio.checked ? '' : 'none'; });
    });

    // --- platforms
    const defaultPlatforms = [
      { key:'zoom_meetings', label:'Zoom Meetings' },
      { key:'zoom_rooms',    label:'Zoom Rooms' },
      { key:'zoom_webinar',  label:'Zoom Webinar' },
      { key:'zoom_phone',    label:'Zoom Phone' },
      { key:'microsoft_teams', label:'Microsoft Teams (E/M add-ons)' },
      { key:'webex_meetings',  label:'Webex Meetings' },
      { key:'webex_calling',   label:'Webex Calling' },
      { key:'google_meet',     label:'Google Meet add-ons' }
    ];
    const platRoot = $('#platforms');

    function platformRow(p){
      const id = `plat_${p.key}_${Math.random().toString(36).slice(2,7)}`;
      const row = document.createElement('div');
      row.className='checkbox-row';
      row.innerHTML = `
        <div><input id="${id}" type="checkbox" aria-describedby="${id}_hint"></div>
        <div>
          <label for="${id}" style="font-weight:700">${p.label}</label>
          <div class="mini-grid">
            <div class="row"><label>Licenses</label><input type="number" min="0" step="1" placeholder="e.g., 120" inputmode="numeric" class="fld-qty" disabled></div>
            <div class="row"><label>Monthly cost / license (USD)</label><input type="number" min="0" step="1" placeholder="optional" inputmode="decimal" class="fld-cost" disabled></div>
            <div class="row"><label>Underuse % (reclaimable)</label><input type="number" min="0" max="100" step="1" placeholder="optional" inputmode="numeric" class="fld-underuse" disabled></div>
          </div>
          <div class="hint" id="${id}_hint">Check to include • add counts & optional cost/underuse % to preview savings.</div>
        </div>`;
      const cb = $('input[type="checkbox"]', row);
      const inputs = $$('.mini-grid input', row);
      cb.addEventListener('change',()=>{ inputs.forEach(i => i.disabled = !cb.checked); updateSavings(); });
      inputs.forEach(i=>i.addEventListener('input', updateSavings));
      row.dataset.platKey = p.key;
      row.dataset.platLabel = p.label;
      platRoot.appendChild(row);
    }
    defaultPlatforms.forEach(platformRow);
    $('#addPlatform').addEventListener('click', ()=>{
      const name = prompt('Custom platform name (e.g., “BlueJeans Events”)');
      if(!name) return; platformRow({ key: name.toLowerCase().replace(/\W+/g,'_'), label: name });
    });
    function updateSavings(){
      const rows = $$('.checkbox-row', platRoot);
      let selected = 0, savings = 0;
      rows.forEach(r=>{
        const checked = $('input[type="checkbox"]', r).checked;
        if(!checked) return; selected++;
        const qty = parseFloat($('.fld-qty', r).value) || 0;
        const cost = parseFloat($('.fld-cost', r).value) || 0;
        const under = Math.min(100, Math.max(0, parseFloat($('.fld-underuse', r).value) || 0));
        savings += qty * cost * (under/100);
      });
      $('#selPlatforms').textContent = `${selected} platform${selected!==1?'s':''} selected`;
      $('#savingsPreview').textContent = money(savings);
    }

    // --- helpers
    function valNum(sel){ const el = document.querySelector(sel); const v = parseFloat(el && el.value); return isFinite(v) ? v : null; }
    function nowIso(){ return new Date().toISOString(); }
    function slug(s){ return String(s||'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,''); }
    function downloadText(filename, text){
      const blob = new Blob([text], {type: 'text/plain;charset=utf-8'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    }

    // --- SOP JSON builder (what you paste with /sop)
    function buildSop(payload){
      const steps = [
        {
          id: "prep_intake_payload",
          title: "Confirm intake payload",
          instruction: "Review captured parameters and confirm scope (rooms, employees, hours, incidents).",
          inputs: payload,
          expected_output: "Signed-off intake payload for baseline run."
        },
        {
          id: "mcp_scaffold",
          title: "Create/verify MCP connections",
          instruction: "Ensure MCP tool configs exist and are reachable.",
          tools: [
            { id: "mcp.zoom",            secrets: ["ZOOM_ACCOUNT_ID","ZOOM_CLIENT_ID","ZOOM_CLIENT_SECRET"] },
            { id: "mcp.zoom_workspaces", secrets: ["ZOOM_WORKSPACES_API_KEY"] },
            { id: "mcp.servicenow",      secrets: ["SN_INSTANCE","SN_USERNAME","SN_TOKEN"] },
            { id: "mcp.25live",          secrets: ["TWENTYFIVELIVE_BASE_URL","TWENTYFIVELIVE_API_KEY"] }
          ],
          expected_output: "All MCP tools registered and authenticated."
        },
        {
          id: "baseline_capture",
          title: "Capture baseline metrics",
          instruction: "Using MCP tools, pull 30-day baseline: meetings, participants, minutes, room utilization, incident rates, and license utilization.",
          expected_output: "Baseline snapshot persisted with evidence (timestamps, queries, counts)."
        },
        {
          id: "kb_seed",
          title: "Seed/Update KB in ServiceNow",
          instruction: "Synthesize an executive-readable baseline summary and post to ServiceNow KB; notify Slack.",
          expected_output: "SN KB article link + Slack message URL."
        },
        {
          id: "schedule_runs",
          title: "Schedule recurring baseline rollups",
          instruction: "Set weekly automation to refresh metrics and track Value Realized deltas.",
          expected_output: "Scheduled workflow entry visible on Dashboard."
        }
      ];

      const how_to = [
        "Click “Download SOP JSON” and paste into Chat with /sop.",
        "Review generated Recipe YAML, save it in Recipes.",
        "Attach the recipe to an agent in Agents.",
        "Create a Workflow “Baseline Capture” using that recipe and run it.",
        "View evidence and deltas in Dashboard; schedule weekly runs."
      ];

      return {
        sop_title: "IPAV Baseline Capture + MCP Scaffold",
        goal: "Establish 30-day baseline and license underuse, then schedule deltas for Value Realized.",
        context: payload,
        steps,
        acceptance_criteria: [
          "MCP tools registered and authenticated.",
          "Baseline snapshot saved with evidence hashes and timestamps.",
          "KB article created/updated with links to evidence and charts.",
          "Slack notification posted to #av-ops (or configured channel)."
        ],
        how_to_implement: how_to,
        meta: { generated_at: nowIso(), schema_version: "1.0.0" }
      };
    }

    // --- YAML builder (preview/importable recipe)
    function yamlEscape(s){ return String(s||'').replace(/"/g,'\\"'); }
    function buildYaml(payload){
      const id = `ipav-baseline-${slug(payload.hours_of_operation || 'hours')}-${Date.now()}`;
      const platforms = (payload.license_optimization?.selected||[]).map(p=>{
        return `      - key: ${p.key}
        label: "${yamlEscape(p.label)}"
        licenses: ${p.licenses ?? 0}
        monthly_cost_per_license_usd: ${p.monthly_cost_per_license_usd ?? 0}
        underuse_percent: ${p.underuse_percent ?? 0}`;
      }).join("\n");

      const meetingsMode = payload.meeting_volume?.mode || "per_room_per_day";
      const mv = payload.meeting_volume || {};
      const incidentsMode = payload.support_incidents?.mode || "per_room";
      const inc = payload.support_incidents || {};

      return `# IPAV Recipe: Baseline Capture + MCP Scaffold
version: "1.0"
recipe:
  id: ${id}
  name: "IPAV Baseline Capture"
  description: >
    Establishes baseline meeting volume, attendance, incident rates, and license utilization.
    Scaffolds MCP tools (Zoom, Zoom Workspaces, ServiceNow, 25Live) and persists a baseline snapshot
    for Value Realized tracking.
  tags: [baseline, value-realized, intake, mcp, ipav]
  parameters:
    avg_attendees_per_meeting: ${payload.avg_attendees_per_meeting ?? 0}
    loaded_cost_per_hour_usd: ${payload.loaded_cost_per_hour_usd ?? 0}
    hours_of_operation: "${yamlEscape(payload.hours_of_operation || '')}"
    environment:
      rooms: ${payload.environment_defaults?.rooms ?? 500}
      employees: ${payload.environment_defaults?.employees ?? 10000}
      stacks: [${(payload.environment_defaults?.stacks||[]).map(s=> '"'+yamlEscape(s)+'"').join(', ')}]
    meeting_volume:
      mode: ${meetingsMode}
      avg_meetings_per_room_per_day: ${mv.avg_meetings_per_room_per_day ?? 0}
      rooms_count: ${mv.rooms_count ?? 0}
      meetings_enterprise_per_month: ${mv.meetings_enterprise_per_month ?? 0}
      employees_count: ${mv.employees_count ?? 0}
    support_incidents:
      mode: ${incidentsMode}
      incidents_per_room_per_month: ${inc.incidents_per_room_per_month ?? 0}
      rooms_count: ${inc.rooms_count ?? 0}
      incidents_enterprise_per_month: ${inc.incidents_enterprise_per_month ?? 0}
    license_candidates:
${platforms ? platforms : "      - {}"}
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
        rooms: \${{params.environment.rooms}}
      save_as: workspaces_util

    - id: compute_incident_baseline
      action: compute
      input:
        mode: \${{params.support_incidents.mode}}
        incidents_per_room_per_month: \${{params.support_incidents.incidents_per_room_per_month}}
        rooms_count: \${{params.support_incidents.rooms_count}}
        incidents_enterprise_per_month: \${{params.support_incidents.incidents_enterprise_per_month}}
      save_as: incidents_baseline

    - id: compute_license_underuse
      action: compute_license_savings
      input:
        candidates: \${{params.license_candidates}}
      save_as: license_baseline

    - id: persist_snapshot
      action: persist_baseline
      input:
        snapshot:
          zoom: \${{steps.fetch_zoom_baseline.output}}
          workspaces: \${{steps.fetch_workspaces_util.output}}
          incidents: \${{steps.compute_incident_baseline.output}}
          licenses: \${{steps.compute_license_underuse.output}}
      save_as: baseline_snapshot

    - id: publish_kb
      action: call
      tool: mcp.servicenow.kb.create_or_update
      input:
        title: "IPAV Baseline Snapshot"
        body_markdown: |
          ## Baseline Snapshot
          Generated: \${{now}}
          ### Zoom
          \${{steps.fetch_zoom_baseline.output}}
          ### Workspaces
          \${{steps.fetch_workspaces_util.output}}
          ### Incidents
          \${{steps.compute_incident_baseline.output}}
          ### Licenses
          \${{steps.compute_license_underuse.output}}
      save_as: kb_article

    - id: notify_slack
      action: call
      tool: mcp.servicenow.notify_slack  # or mcp.slack.post if you use a Slack MCP
      input:
        channel: "#av-ops"
        text: "Baseline snapshot ready — KB: \${{steps.publish_kb.output.url}}"

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
 `;
    }

    // --- serialize intake → payload
    function makePayload(){
      const meeting = (()=> {
        const mode = document.querySelector('input[name="meet_mode"]:checked').value;
        if(mode === 'per_room_per_day'){
          return {
            mode,
            avg_meetings_per_room_per_day: valNum('#mtgs_per_room_day'),
            rooms_count: valNum('#rooms_count')
          };
        } else {
          return {
            mode,
            meetings_enterprise_per_month: valNum('#mtgs_enterprise_month'),
            employees_count: valNum('#employees_count')
          };
        }
      })();

      const incidents = (()=> {
        const mode = document.querySelector('input[name="inc_mode"]:checked').value;
        if(mode === 'per_room'){
          return {
            mode,
            incidents_per_room_per_month: valNum('#incidents_per_room_month'),
            rooms_count: valNum('#rooms_count_inc')
          };
        } else {
          return {
            mode,
            incidents_enterprise_per_month: valNum('#incidents_enterprise_month'),
            rooms_count_reference: valNum('#rooms_count_inc_ro')
          };
        }
      })();

      const hoursSel = document.querySelector('input[name="hours"]:checked').value;
      const hours = hoursSel === 'custom' ? (document.querySelector('#hours_custom').value || 'custom') : hoursSel;

      const rows = Array.from(document.querySelectorAll('.checkbox-row', platRoot));
      const selected = [];
      rows.forEach(r=>{
        const cb = r.querySelector('input[type="checkbox"]');
        if(!cb.checked) return;
        selected.push({
          key: r.dataset.platKey,
          label: r.dataset.platLabel,
          licenses: parseFloat(r.querySelector('.fld-qty').value) || 0,
          monthly_cost_per_license_usd: parseFloat(r.querySelector('.fld-cost').value) || null,
          underuse_percent: parseFloat(r.querySelector('.fld-underuse').value) || null
        });
      });
      const est_monthly_savings = selected.reduce((acc,p)=>{
        const qty = p.licenses||0, cost = p.monthly_cost_per_license_usd||0, under = Math.min(100,Math.max(0,p.underuse_percent||0));
        return acc + qty*cost*(under/100);
      }, 0);

      return {
        meeting_volume: meeting,
        avg_attendees_per_meeting: valNum('#avg_attendees'),
        loaded_cost_per_hour_usd: valNum('#loaded_cost_hour'),
        support_incidents: incidents,
        hours_of_operation: hours,
        license_optimization: { selected, est_monthly_savings },
        environment_defaults: { rooms: 500, employees: 10000, stacks: ["Zoom","Q-SYS","Crestron","Logitech"] },
        meta: { generated_at: nowIso(), schema_version: "1.0.0" }
      };
    }

    // --- validation helpers
    function validatePayload(payload){
      const errors = [];
      const warn = [];
      // meeting volume
      const mv = payload.meeting_volume || {};
      if(mv.mode === 'per_room_per_day'){
        const perDay = parseFloat(mv.avg_meetings_per_room_per_day);
        if(!isFinite(perDay) || perDay < 0 || perDay > 24){
          errors.push('Avg meetings per room per day must be between 0 and 24.');
        }
        if(!mv.rooms_count || mv.rooms_count <= 0){
          errors.push('Rooms count must be a positive number.');
        }
      } else {
        if(!mv.meetings_enterprise_per_month || mv.meetings_enterprise_per_month < 0){
          errors.push('Enterprise meetings per month must be non-negative.');
        }
        if(!mv.employees_count || mv.employees_count <= 0){
          errors.push('Employees count must be a positive number.');
        }
      }
      // support incidents
      const inc = payload.support_incidents || {};
      if(inc.mode === 'per_room'){
        if(!inc.incidents_per_room_per_month || inc.incidents_per_room_per_month < 0){
          errors.push('Incidents per room per month must be non-negative.');
        }
        if(!inc.rooms_count || inc.rooms_count <= 0){
          errors.push('Rooms count for incidents must be positive.');
        }
      } else {
        if(!inc.incidents_enterprise_per_month || inc.incidents_enterprise_per_month < 0){
          errors.push('Incidents per month must be non-negative.');
        }
      }
      // license optimization
      (payload.license_optimization?.selected || []).forEach(p => {
        if(p.licenses && p.licenses <= 0){
          errors.push(`Platform ${p.label}: license count must be greater than 0.`);
        }
        if(p.underuse_percent && (p.underuse_percent < 0 || p.underuse_percent > 100)){
          errors.push(`Platform ${p.label}: underuse % must be between 0 and 100.`);
        }
        if(p.underuse_percent > 25){
          warn.push(`${p.label}: underuse > 25%; consider reducing licenses.`);
        }
      });
      return { errors, warn };
    }
  // Helper to check radios and fire change toggles
  function checkAndChange(el){
    if (!el) return;
    el.checked = true;
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }

  // Set a platform row by key; checks the box, enables inputs, sets values
  function setPlatformSample(key, { qty=0, cost=0, under=0 } = {}){
    const row = platRoot.querySelector(`.checkbox-row[data-plat-key="${key}"]`);
    if(!row) return;
    const cb = row.querySelector('input[type="checkbox"]');
    const qtyEl = row.querySelector('.fld-qty');
    const costEl = row.querySelector('.fld-cost');
    const underEl = row.querySelector('.fld-underuse');

    cb.checked = true;
    cb.dispatchEvent(new Event('change', { bubbles: true })); // enables inputs
    qtyEl.value = qty;
    costEl.value = cost;
    underEl.value = under;
  }

  // Load canonical demo values and auto-generate outputs
  function loadSampleValues(){
    // Meetings: per room per day
    checkAndChange(document.querySelector('#mode_room_day'));
    document.querySelector('#mtgs_per_room_day').value = 5; // typical
    document.querySelector('#rooms_count').value = 500;

    // Attendees & cost
    document.querySelector('#avg_attendees').value = 6;
    document.querySelector('#loaded_cost_hour').value = 85;

    // Incidents: per room per month
    checkAndChange(document.querySelector('#inc_mode_room'));
    document.querySelector('#incidents_per_room_month').value = 0.3;
    document.querySelector('#rooms_count_inc').value = 500;

    // Hours of operation: 9–5 weekdays
    const hrs = Array.from(document.querySelectorAll('input[name="hours"]'))
      .find(r => r.value === '9-5 weekdays');
    checkAndChange(hrs);

    // License samples (kept modest to avoid validation warnings)
    setPlatformSample('zoom_meetings', { qty: 10000, cost: 15, under: 10 });
    setPlatformSample('zoom_rooms',    { qty: 500,   cost: 50, under: 20 });
    setPlatformSample('zoom_phone',    { qty: 8000,  cost: 8,  under: 15 });
    setPlatformSample('zoom_webinar',  { qty: 120,   cost: 90, under: 10 });

    updateSavings();

    // One-click: submit to generate previews
    const form = document.querySelector('#intake');
    if (form && typeof form.requestSubmit === 'function') {
      form.requestSubmit();
    } else if (form) {
      form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    }

    // Bring results into view
    const jsonOut = document.querySelector('#jsonOut');
    if (jsonOut) jsonOut.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Wire the new button
  document.addEventListener('DOMContentLoaded', ()=>{
    const btn = document.querySelector('#loadSample');
    if (btn) btn.addEventListener('click', loadSampleValues);
  });
    // --- wire buttons
    $('#intake').addEventListener('submit', (e)=>{
      e.preventDefault();
      const payload = makePayload();
      const { errors, warn } = validatePayload(payload);
      const msgBox = document.querySelector('#copyState');
      msgBox.className = 'small';
      if(errors.length){
        msgBox.textContent = errors.join(' ');
        msgBox.classList.add('warn');
        return;
      }
      if(warn.length){
        msgBox.textContent = warn.join(' ');
        msgBox.classList.add('warn');
      }
      const sop = buildSop(payload);
      const yaml = buildYaml(payload);
      document.querySelector('#jsonOut').value = JSON.stringify(sop, null, 2);
      document.querySelector('#yamlOut').value = yaml;
    });

    document.querySelector('#copyJson').addEventListener('click', async ()=>{
      const txt = document.querySelector('#jsonOut').value.trim();
      const copyState = document.querySelector('#copyState');
      if(!txt){ copyState.textContent = 'Generate first.'; return; }
      try{ await navigator.clipboard.writeText(txt); copyState.textContent = 'SOP JSON copied ✓'; copyState.className = 'small success';
      }catch{ copyState.textContent = 'Copy failed — select & copy manually.'; copyState.className = 'small warn'; }
      setTimeout(()=>{copyState.textContent='';}, 2000);
    });

    document.querySelector('#copyYaml').addEventListener('click', async ()=>{
      const txt = document.querySelector('#yamlOut').value.trim();
      const copyState = document.querySelector('#copyState');
      if(!txt){ copyState.textContent = 'Generate first.'; return; }
      try{ await navigator.clipboard.writeText(txt); copyState.textContent = 'YAML copied ✓'; copyState.className = 'small success';
      }catch{ copyState.textContent = 'Copy failed — select & copy manually.'; copyState.className = 'small warn'; }
      setTimeout(()=>{copyState.textContent='';}, 2000);
    });

    document.querySelector('#downloadSop').addEventListener('click', ()=>{
      const txt = document.querySelector('#jsonOut').value.trim();
      if(!txt){ alert('Generate first.'); return; }
      downloadText('ipav_baseline_sop.json', txt);
    });

    document.querySelector('#downloadYaml').addEventListener('click', ()=>{
      const txt = document.querySelector('#yamlOut').value.trim();
      if(!txt){ alert('Generate first.'); return; }
      downloadText('ipav_baseline_recipe.yaml', txt);
    });
  </script>
</body>
</html>"""

# Render the intake form.  Adjust height as needed when expanding instructions.
components.html(form_html, height=2100, scrolling=True)
