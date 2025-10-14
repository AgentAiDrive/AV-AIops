import { all, get } from '../db/store.js';
export function Review(){
  const div=document.createElement('div');
  div.innerHTML=`<h2>Review</h2><div class="card"><pre class="mono" id="dump"></pre><button class="btn" id="go">Proceed to Launch</button></div>`;
  (async()=>{
    const cfg={global:await get('config','global'),integrations:await get('config','integrations'),agents:await get('config','agents'),optimization:await get('config','optimization'),recipes:await all('recipes')};
    div.querySelector('#dump').textContent=JSON.stringify(cfg,null,2);
  })();
  div.querySelector('#go').onclick=()=>location.hash='#/launch';
  return div;
}
