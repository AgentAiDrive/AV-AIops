import { put } from '../db/store.js';
const AGENTS=['conductor','support-requests','incidents','projects','events','recipe-library','baseline-dashboards','incident-outcome-mapper','kb-recipe-scout'];
export function Agents(){
  const div=document.createElement('div');
  const boxes=AGENTS.map(a=>`<label><input type="checkbox" class="ag" data-k="${a}" checked> ${a}</label>`).join('<br>');
  div.innerHTML=`<h2>Agents</h2><div class="card">${boxes}</div><button class="btn" id="save">Save</button>`;
  div.querySelector('#save').onclick=async()=>{
    const sel=[...div.querySelectorAll('.ag')].filter(x=>x.checked).map(x=>x.dataset.k);
    await put('config',{id:'agents',enabled:sel}); alert('Saved. Continue to Optimization.'); location.hash='#/optimization';
  };
  return div;
}
