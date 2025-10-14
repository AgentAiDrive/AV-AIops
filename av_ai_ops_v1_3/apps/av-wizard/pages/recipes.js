import { put } from '../db/store.js';
const PRESETS=[
 {id:'lighting_neutral_presentations', name:'Neutral Presentation Lighting', hypothesis:'Neutral CT (~4000K) improves readability.', knobs:{lighting:{ct_kelvin:4000,level:0.7}}, metrics:{primary:'retention_proxy'}, guardrails:{rollback_if:'csat < 6'}, risk:'low'},
 {id:'audio_qna_gain_boost', name:'Audience Q&A Gain Boost', hypothesis:'Gain boost raises Q&A participation.', knobs:{audio:{audience_mic_gain_db:3}}, metrics:{primary:'qna_count'}, guardrails:{rollback_if:'feedback_events > baseline'}, risk:'medium'}
];
export function Recipes(){
  const div=document.createElement('div');
  const cards=PRESETS.map(r=>`<div class="card"><b>${r.name}</b><div class="muted">${r.hypothesis}</div><button class="btn add" data-id="${r.id}">Add</button></div>`).join('');
  div.innerHTML=`<h2>Recipes</h2><div class="grid grid-2">${cards}</div>`;
  div.addEventListener('click', async (e)=>{
    const b=e.target.closest('.add'); if(!b) return;
    const r=PRESETS.find(x=>x.id===b.dataset.id);
    await put('recipes',{id:r.id,...r}); b.disabled=true; b.textContent='Added';
  });
  return div;
}
