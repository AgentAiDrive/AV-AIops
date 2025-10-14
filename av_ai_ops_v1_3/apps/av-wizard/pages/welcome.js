import { put } from '../db/store.js';
export function Welcome(){
  const div=document.createElement('div');
  div.innerHTML=`<h2>Welcome</h2>
    <div class="card grid">
      <label>Mode</label>
      <select id="mode"><option value="mock">Mock</option><option value="real">Real (with MCP)</option></select>
      <label>Project Name</label><input id="project" value="Executive Briefing Pilot"/>
      <button class="btn" id="save">Save</button>
    </div>`;
  div.querySelector('#save').onclick=async()=>{
    await put('config',{id:'global',mode:div.querySelector('#mode').value,project:div.querySelector('#project').value});
    alert('Saved. Continue to Integrations.'); location.hash='#/integrations';
  };
  return div;
}
