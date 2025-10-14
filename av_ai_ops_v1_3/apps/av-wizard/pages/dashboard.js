import { all, get } from "../db/store.js";
import { ensureSeed } from "../db/seed.js";
import { lineChart, barChart } from "../lib/charts.js";

export function Dashboard(){
  const div=document.createElement("div");
  div.innerHTML=`<h2>Dashboard</h2>
  <div class="grid grid-2">
    <div class="card"><h3>Agent Health</h3><div id="health"></div><div class="caption">Latency p95 & error rate per agent with status.</div></div>
    <div class="card"><h3>Value Realized (Sim)</h3>
      <div class="row"><div class="kpi" id="valueUsd">$â€”</div><span class="badge good">â†‘ improving</span></div>
      <div class="caption">Quarterly estimate based on readiness lift, MTTR drop, and avoided incidents.</div>
    </div>

    <div class="card"><h3>Event Readiness (%)</h3><div class="canvas-wrap"><canvas id="c_ready" class="chart"></canvas></div><div class="caption">Pre-flight pass rate before go-live.</div></div>
    <div class="card"><h3>MTTR (minutes)</h3><div class="canvas-wrap"><canvas id="c_mttr" class="chart"></canvas></div><div class="caption">Mean time to resolve for known issues.</div></div>

    <div class="card"><h3>Failed Starts per 100 Meetings</h3><div class="canvas-wrap"><canvas id="c_fail" class="chart"></canvas></div><div class="caption">Lower is better; affected by self-heal coverage and device stability.</div></div>
    <div class="card"><h3>Auto-Resolves per Week</h3><div class="canvas-wrap"><canvas id="c_auto" class="chart"></canvas></div><div class="caption">Incidents closed by agents without human escalation.</div></div>

    <div class="card"><h3>Top Rooms by Incidents</h3><ul id="rooms" class="list"></ul><div class="caption">Focus remediation or upgrades where incidents cluster.</div></div>
    <div class="card"><h3>Upcoming Events â€” Preflight</h3><ul id="preflights" class="list"></ul><div class="caption">Automated checks: platform, devices, encoders, calendar.</div></div>

    <div class="card" style="grid-column:1/-1">
      <h3>Architecture & Workflow</h3>
      <div id="arch"></div>
      <div class="caption">Large-model orchestrator plans/validates; small-model/connector agents act across tools. Unified swimlane: Intake â†’ Plan â†’ Act â†’ Verify.</div>
    </div>

    <div class="card" style="grid-column:1/-1">
      <h3>Logs</h3><pre id="logs" class="mono"></pre>
    </div>
  </div>`;

  (async()=>{
    await ensureSeed();
    const t = await get("telemetry","demo");
    const logs = await all("logs");
    const health = await get("health","agents");

    const h = health?.items||[];
    const badge = (s)=> s==="ok" ? "good" : (s==="warn" ? "warn":"bad");
    const rows = h.map(a=>`<tr>
      <td><span class="pill">${a.name}</span></td>
      <td>${a.p95_ms} ms</td>
      <td>${a.error_rate}%</td>
      <td><span class="badge ${badge(a.status)}">${a.status}</span></td>
      <td class="muted small">${a.desc}</td>
    </tr>`).join("");
    div.querySelector("#health").innerHTML = `<table class="table"><thead><tr><th>Agent</th><th>p95</th><th>Error</th><th>Status</th><th>About</th></tr></thead><tbody>${rows}</tbody></table>`;

    const latestReadiness = t.readiness.at(-1);
    const latestMttr = t.mttrMin.at(-1);
    const avoided = Math.max(0, (t.failedStarts[0]-t.failedStarts.at(-1)))*12;
    const value = Math.round( latestReadiness*120 + (70-latestMttr)*200 + avoided*150 );
    div.querySelector("#valueUsd").textContent = `$${value.toLocaleString()}`;

    lineChart(div.querySelector("#c_ready"), t.readiness);
    lineChart(div.querySelector("#c_mttr"), t.mttrMin);
    lineChart(div.querySelector("#c_fail"), t.failedStarts);
    barChart(div.querySelector("#c_auto"), t.autoResolves);

    div.querySelector("#rooms").innerHTML = t.incidentsByRoom.map(r=>`<li class="flex justify-between"><span>${r.room}</span><b>${r.count}</b></li>`).join("");
    div.querySelector("#preflights").innerHTML = t.preflights.map(p=>`<li class="flex justify-between"><span>${p.event}</span><span class="badge ${p.status==="Ready"?"good":"warn"}">${p.status}</span></li>`).join("");

    div.querySelector("#arch").innerHTML = `
    <svg viewBox="0 0 900 250" width="100%" height="220" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="g" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="#0ea5e9"/><stop offset="100%" stop-color="#7dd3fc"/>
        </linearGradient>
        <style>
          .lane{fill:#0b1220;stroke:#334155;stroke-width:1}
          .box{fill:#111827;stroke:#334155;stroke-width:1}
          .txt{fill:#e2e8f0;font:600 12px Inter, sans-serif}
          .mut{fill:#94a3b8;font:500 11px Inter, sans-serif}
          .arrow{stroke:url(#g);stroke-width:3;marker-end:url(#m)}
        </style>
        <marker id="m" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L0,6 L6,3 z" fill="#7dd3fc"/>
        </marker>
      </defs>
      <rect class="lane" x="10" y="20"  width="880" height="60" rx="10"/><text class="mut" x="20" y="35">Onsite Team</text>
      <rect class="lane" x="10" y="100" width="880" height="60" rx="10"/><text class="mut" x="20" y="115">Central Hub / Cloud</text>
      <rect class="lane" x="10" y="180" width="880" height="60" rx="10"/><text class="mut" x="20" y="195">AVoAI Orchestrator (Large Model) & Connector Agents (Small Models)</text>
      <g transform="translate(110,30)">
        <rect class="box" x="0"   y="0" width="130" height="40" rx="8"/><text class="txt" x="65" y="25" text-anchor="middle">Intake</text>
        <line class="arrow" x1="130" y1="20" x2="170" y2="20"/>
        <rect class="box" x="170" y="0" width="130" height="40" rx="8"/><text class="txt" x="235" y="25" text-anchor="middle">Plan</text>
        <line class="arrow" x1="300" y1="20" x2="340" y2="20"/>
        <rect class="box" x="340" y="0" width="130" height="40" rx="8"/><text class="txt" x="405" y="25" text-anchor="middle">Act</text>
        <line class="arrow" x1="470" y1="20" x2="510" y2="20"/>
        <rect class="box" x="510" y="0" width="130" height="40" rx="8"/><text class="txt" x="575" y="25" text-anchor="middle">Verify</text>
      </g>
      <text class="mut" x="120" y="75">Intake: form/Slack; signal collection</text>
      <text class="mut" x="120" y="155">Act: mixing/encoding/UC setup</text>
      <text class="mut" x="120" y="235">Plan/Verify: tool selection, guardrails, outcomes</text>
    </svg>`;

    div.querySelector("#logs").textContent=(logs||[]).map(x=>`[${new Date(x.ts).toISOString()}] ${x.msg}`).join("\\n");
  })();

  return div;
}