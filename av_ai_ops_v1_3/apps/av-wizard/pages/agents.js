import { put } from "../db/store.js";
const AGENTS=[
  ["conductor","Routes tasks, approvals, and SLAs across agents"],
  ["support-requests","/avhelp intake, triage, targeted actions"],
  ["incidents","Self-heal runbooks + escalation with artifacts"],
  ["projects","Builds/changes stories, tasks, and CMDB links"],
  ["events","Event planning, rehearsals, live ops, postmortems"],
  ["recipe-library","YAML recipes; schema guardrails; promotions"],
  ["baseline-dashboards","Telemetry snapshots and KPI cards"],
  ["incident-outcome-mapper","Correlation views: incidents + outcomes"],
  ["kb-recipe-scout","Web search, KB synth, add recipe, create ServiceNow KB]
];
export function Agents(){
  const div=document.createElement("div");
  const boxes=AGENTS.map(([k,tip])=>`<label class="tooltip" data-tip="${tip}"><input type="checkbox" class="ag" data-k="${k}" checked> ${k}</label>`).join("<br>");
  div.innerHTML=`<h2>Agents</h2>
    <div class="card">${boxes}<div class="caption">Hover any agent to see what it does. Uncheck to disable during the pilot.</div></div>
    <button class="btn" id="save">Save</button>`;
  div.querySelector("#save").onclick=async()=>{
    const sel=[...div.querySelectorAll(".ag")].filter(x=>x.checked).map(x=>x.dataset.k);
    await put("config",{id:"agents",enabled:sel}); alert("Saved. Continue to Optimization."); location.hash="#/optimization";
  };
  return div;
}