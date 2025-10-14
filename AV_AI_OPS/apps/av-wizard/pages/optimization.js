import { put } from '../db/store.js';
export function Optimization(){
  const div=document.createElement('div');
  div.innerHTML=`<h2>Optimization — Executive Briefing Rooms</h2>
  <div class="card grid">
    <label>KPIs</label>
    <label><input type="checkbox" class="kpi" data-k="decision_reached" checked> decision_reached</label>
    <label><input type="checkbox" class="kpi" data-k="followup_booked" checked> followup_booked</label>
    <label><input type="checkbox" class="kpi" data-k="csat" checked> csat</label>
    <label><input type="checkbox" class="kpi" data-k="engagement_proxy" checked> engagement_proxy</label>
    <label><input type="checkbox" class="kpi" data-k="issue_rate_per_100" checked> issue_rate_per_100</label>
    <label><input type="checkbox" class="kpi" data-k="join_latency_s" checked> join_latency_s</label>
    <label>Bandit Strategy</label>
    <select id="strategy"><option>epsilon_greedy</option><option>uniform_ab</option></select>
    <label>Notes</label><textarea id="notes" placeholder="Goals, context..."></textarea>
    <button class="btn" id="save">Save</button>
  </div>`;
  div.querySelector('#save').onclick=async()=>{
    const ks=[...div.querySelectorAll('.kpi')].filter(x=>x.checked).map(x=>x.dataset.k);
    await put('config',{id:'optimization',kpis:ks,strategy:div.querySelector('#strategy').value,notes:div.querySelector('#notes').value});
    alert('Saved. Continue to Recipes.'); location.hash='#/recipes';
  };
  return div;
}
