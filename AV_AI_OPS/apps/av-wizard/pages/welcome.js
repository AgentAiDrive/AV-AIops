// apps/av-wizard/pages/welcome.js
import { put } from '../db/store.js';

export function Welcome() {
  const div = document.createElement('div');

  div.innerHTML = `
    <h2>Welcome</h2>
    <p class="muted">This wizard guides you through a pilot setup, integrations, agents, optimization, and launch. You can run entirely in mock mode or connect to local MCP tool servers.</p>

    <!-- Quick Setup (TOP) -->
    <div class="card" style="margin:14px 0 22px">
      <h3 style="margin:0 0 8px 0">Quick Setup</h3>
      <div class="grid" style="grid-template-columns: 160px 1fr; gap:10px">
        <label for="mode" class="muted">Mode</label>
        <select id="mode">
          <option value="mock" selected>Mock</option>
          <option value="real">Real (with MCP)</option>
        </select>

        <label for="project" class="muted">Project Name</label>
        <input id="project" value="Executive Briefing Pilot" />

        <div></div>
        <div class="row" style="justify-content:flex-start; gap:8px">
          <button class="btn" id="save">Save & Continue → Integrations</button>
        </div>
      </div>
    </div>

    <div class="hr"></div>
    <h3>Legend — What the badges mean</h3>
    <div class="grid grid-3">
      <div class="card">
        <b>Static HTML/JS</b>
        <p class="muted">
          Pure ES-module app, no build. Open <code>index.html</code> via a local server
          (e.g., <code>python -m http.server</code>) to avoid <code>file://</code> module limits.
        </p>
        <ul class="muted">
          <li>Double-click <code>index.html</code> (mock mode works in most browsers)</li>
          <li>Or serve: <code>python -m http.server 5173 -d apps/av-wizard</code></li>
        </ul>
      </div>
      <div class="card">
        <b>IndexedDB</b>
        <p class="muted">
          Local browser DB. Stores your config, recipes, and logs. Export/Import JSON from the
          <em>Review</em> step or the <em>Dashboard</em> (if enabled).
        </p>
        <ul class="muted">
          <li>Resilient across reloads</li>
          <li>No secrets stored in the browser (integrations go via MCP servers)</li>
        </ul>
      </div>
      <div class="card">
        <b>Web Workers</b>
        <p class="muted">
          Agents (events, incidents, recipes, dashboards, scout) run off-thread.
          In mock mode they simulate external tools; in real mode they call your local MCP servers.
        </p>
        <ul class="muted">
          <li>Non-blocking UI</li>
          <li>Task queue + simple retries/backoff</li>
        </ul>
      </div>
    </div>

    <div class="hr"></div>
    <h3>How to — File tree</h3>
    <pre class="muted" style="white-space:pre; overflow:auto; max-height:40vh"><code>
apps/
  av-wizard/
    index.html                 # main page (ES modules)
    styles/tailwind-lite.css   # small utility CSS
    lib/
      router.js                # hash router (#/welcome, etc.)
    db/
      store.js                 # IndexedDB helpers
    pages/
      welcome.js               # this page (legend, file tree)
      integrations.js          # set MCP endpoints (mock vs localhost)
      agents.js                # enable/disable browser agents
      optimization.js          # KPIs + bandit strategy + notes
      recipes.js               # recipe cards -> Recipe Library
      review.js                # export/import config
      launch.js                # start agents / run checks
      dashboard.js             # health, logs, value realized, library
    workers/
      agent-conductor.js
      agent-events.js
      agent-support-requests.js
      agent-incidents.js
      agent-projects.js
      agent-recipe-library.js
      agent-baseline-dashboards.js
      agent-incident-outcome-mapper.js
      agent-kb-recipe-scout.js

mcp-tools/                     # optional local tool servers
  mcp-slack/                   # Slack bot proxy (CORS, .env)
  mcp-zoom/                    # Zoom admin/webinar proxy
  mcp-servicenow/              # ServiceNow KB/Story proxy
  mcp-github/
  mcp-gdrive/
  mcp-search/

scripts/
  win/
    start_all_mcp.bat          # launch all MCP servers on Windows

packages/
  recipes/                     # YAML/JSONC recipes + OpenAI packs
  schemas/                     # JSON Schemas
  value-reporting/             # Value Realized helpers

docs/                          # README, setup, integrations, runbooks
    </code></pre>

    <div class="hr"></div>
    <h3>Quick start</h3>
    <ol class="muted">
      <li>Run in <b>Mock</b>: open <code>apps/av-wizard/index.html</code>.</li>
      <li>Run with real tools: start local MCP servers (<code>scripts/win/start_all_mcp.bat</code>), then set endpoints in <em>Integrations</em>.</li>
      <li>Select KPIs & strategy in <em>Optimization</em>, add a few recipes, <em>Launch</em>, then watch <em>Dashboard</em>.</li>
    </ol>
  `;

  // Wire Quick Setup save
  const modeEl = div.querySelector('#mode');
  const projectEl = div.querySelector('#project');
  const saveBtn = div.querySelector('#save');

  if (saveBtn) {
    saveBtn.onclick = async () => {
      const mode = modeEl?.value || 'mock';
      const project = projectEl?.value?.trim() || 'Executive Briefing Pilot';
      await put('config', { id: 'global', mode, project, updated_at: Date.now() });
      alert('Saved. Continue to Integrations.');
      location.hash = '#/integrations';
    };
  }

  return div;
}
