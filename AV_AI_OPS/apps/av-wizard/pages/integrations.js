import { put } from '../db/store.js';
export function Integrations(){
  const div=document.createElement('div');
  div.innerHTML=`<h2>Integrations</h2>
  <div class="card grid grid-2">
    <div><label>Slack MCP</label><input id="slack" value="http://localhost:8401"></div>
    <div><label>Zoom MCP</label><input id="zoom" value="http://localhost:8402"></div>
    <div><label>GitHub MCP</label><input id="github" value="http://localhost:8403"></div>
    <div><label>Google Drive MCP</label><input id="gdrive" value="http://localhost:8404"></div>
    <div><label>ServiceNow MCP</label><input id="snow" value="http://localhost:8405"></div>
    <div><label>Search MCP</label><input id="search" value="http://localhost:8406"></div>
    <button class="btn" id="save">Save</button>
  </div>`;
  div.querySelector('#save').onclick=async()=>{
    await put('config',{
      id:'integrations',
      slack:div.querySelector('#slack').value, zoom:div.querySelector('#zoom').value,
      github:div.querySelector('#github').value, gdrive:div.querySelector('#gdrive').value,
      snow:div.querySelector('#snow').value, search:div.querySelector('#search').value
    });
    alert('Saved. Move to Agents.'); location.hash='#/agents';
  };
  return div;
}
