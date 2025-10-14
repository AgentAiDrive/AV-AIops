import { all } from '../db/store.js';
export function Dashboard(){
  const div=document.createElement('div');
  div.innerHTML=`<h2>Dashboard</h2>
    <div class="grid grid-2">
      <div class="card"><h3>Agent Health</h3><div id="health"></div></div>
      <div class="card"><h3>Value Realized (Demo)</h3><div id="value"></div></div>
      <div class="card"><h3>Logs</h3><pre id="logs" class="mono"></pre></div>
      <div class="card"><h3>Recipe Library</h3><div id="recipes"></div></div>
    </div>`;
  (async()=>{
    const logs=await all('logs'); const recipes=await all('recipes');
    div.querySelector('#logs').textContent=(logs||[]).map(x=>`[${x.ts}] ${x.msg}`).join('\n');
    div.querySelector('#recipes').innerHTML=(recipes||[]).map(r=>`<div class="card"><b>${r.name}</b><div class="muted">${r.hypothesis}</div></div>`).join('');
    const vr={wins:3, quarterly_gain_usd:125000};
    div.querySelector('#value').innerHTML = `<div class="card">Wins: <b>${vr.wins}</b><br>Estimated Value: <b>$${vr.quarterly_gain_usd.toLocaleString()}</b></div>`;
    const agents=['conductor','support-requests','incidents','projects','events','recipe-library','baseline-dashboards','incident-outcome-mapper','kb-recipe-scout'];
    div.querySelector('#health').innerHTML = agents.map(a=>`<span class="pill">✅ ${a}</span>`).join(' ');
  })();
  return div;
}
