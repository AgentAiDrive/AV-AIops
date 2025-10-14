import { get } from '../db/store.js';
export function Launch(){
  const div=document.createElement('div');
  div.innerHTML=`<h2>Launch</h2><div id="log" class="card mono" style="white-space:pre"></div><button class="btn" id="dash">Open Dashboard</button>`;
  const log=(m)=>{div.querySelector('#log').textContent += m+"\n";};
  (async()=>{
    const agents=(await get('config','agents'))?.enabled||[];
    for(const a of agents){
      try{ const w=new Worker(`../workers/agent-${a}.js`,{type:'module'}); w.onmessage=(e)=>log(`[${a}] ${e.data}`); w.postMessage({type:'start'}); }
      catch(e){ log(`[${a}] failed to start: ${e.message}`); }
    }
    log('Workers started. Switch to Dashboard.');
  })();
  div.querySelector('#dash').onclick=()=>location.hash='#/dashboard';
  return div;
}
