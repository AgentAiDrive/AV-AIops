import { put, get, ensureStores } from './store.js';

export async function ensureSeed(){
  await ensureStores();
  const existing = await get('telemetry','demo');
  if (existing) return;

  const rnd = (n)=> Math.round(n*100)/100;
  const weeks = Array.from({length:12}, (_,i)=>i);

  const mttrMin      = weeks.map(i=> rnd(65 - i*2 + (Math.random()*6-3)));
  const readiness    = weeks.map(i=> rnd(78 + i*1.5 + (Math.random()*3-1.5)));
  const failedStarts = weeks.map(i=> rnd(10 - i*0.7 + (Math.random()*2-1)));
  const autoResolves = weeks.map(i=> Math.round(20 + i*1.8 + (Math.random()*6-3)));

  const incidentsByRoom = [
    { room:'HQ-AUD-1', count: 8 },
    { room:'HQ-TH-2',  count: 6 },
    { room:'NYC-CR-5', count: 4 },
    { room:'LDN-HUD-3',count: 3 }
  ];
  const preflights = [
    { event:'All-Hands 10/18', status:'Ready',     checks:18, issues:0 },
    { event:'QBR 10/22',      status:'Attention',  checks:16, issues:2 },
    { event:'Training 10/25', status:'Ready',      checks:14, issues:0 }
  ];

  await put('telemetry',{ id:'demo', mttrMin, readiness, failedStarts, autoResolves, incidentsByRoom, preflights, ts: Date.now() });
  await put('health',{ id:'agents', items: [
    { name:'conductor', p95_ms:180, error_rate:0.2, status:'ok',   desc:'Routes tasks and enforces SLAs' },
    { name:'support-requests', p95_ms:240, error_rate:0.5, status:'ok',   desc:'/avhelp intake to triage' },
    { name:'incidents', p95_ms:260, error_rate:0.7, status:'ok',   desc:'Self-heal runbooks and escalation' },
    { name:'projects', p95_ms:220, error_rate:0.4, status:'ok',   desc:'Builds/changes scaffolding' },
    { name:'events', p95_ms:310, error_rate:0.9, status:'warn', desc:'Rehearsal/live orchestration' },
    { name:'recipe-library', p95_ms:150, error_rate:0.1, status:'ok',   desc:'YAML recipes + guardrails' },
    { name:'baseline-dashboards', p95_ms:130, error_rate:0.1, status:'ok',   desc:'Snapshots & KPIs' },
    { name:'incident-outcome-mapper', p95_ms:280, error_rate:1.1, status:'ok',   desc:'Outcome correlation views' },
    { name:'kb-recipe-scout', p95_ms:420, error_rate:1.5, status:'ok',   desc:'Docs â†’ KB â†’ Recipe â†’ Slack' }
  ]});
}