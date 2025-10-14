export function lineChart(canvas, series, opts={}) {
  const ctx = canvas.getContext('2d');
  const W = canvas.width = canvas.clientWidth;
  const H = canvas.height = canvas.clientHeight;
  ctx.clearRect(0,0,W,H);
  const padding = 20;
  const xmin = 0, xmax = series.length - 1;
  const ymin = Math.min(...series), ymax = Math.max(...series);
  const ypad = (ymax - ymin) || 1;
  const sx = (x)=> padding + (x - xmin) / (xmax - xmin || 1) * (W - 2*padding);
  const sy = (y)=> H - padding - (y - ymin) / ypad * (H - 2*padding);
  ctx.strokeStyle='rgba(148,163,184,.25)'; ctx.lineWidth=1;
  for (let i=0;i<=4;i++){ const y=padding+i*(H-2*padding)/4; ctx.beginPath(); ctx.moveTo(padding,y); ctx.lineTo(W-padding,y); ctx.stroke(); }
  ctx.strokeStyle='#7dd3fc'; ctx.lineWidth=2; ctx.beginPath();
  series.forEach((v,i)=>{ const x=sx(i), y=sy(v); if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y); });
  ctx.stroke();
  ctx.fillStyle='#38bdf8';
  series.forEach((v,i)=>{ const x=sx(i), y=sy(v); ctx.beginPath(); ctx.arc(x,y,2.5,0,Math.PI*2); ctx.fill(); });
}
export function barChart(canvas, series) {
  const ctx = canvas.getContext('2d');
  const W = canvas.width = canvas.clientWidth;
  const H = canvas.height = canvas.clientHeight;
  ctx.clearRect(0,0,W,H);
  const padding = 20; const n = series.length;
  const ymax = Math.max(1, ...series);
  const bw = (W - 2*padding)/n * .7;
  ctx.strokeStyle='rgba(148,163,184,.25)'; ctx.lineWidth=1;
  for (let i=0;i<=4;i++){ const y=padding+i*(H-2*padding)/4; ctx.beginPath(); ctx.moveTo(padding,y); ctx.lineTo(W-padding,y); ctx.stroke(); }
  series.forEach((v,i)=>{
    const x=padding + (i+0.15)*(W-2*padding)/n; const h=(v/ymax)*(H-2*padding); const y=H-padding-h;
    ctx.fillStyle='#60a5fa'; ctx.fillRect(x,y,bw,h);
  });
}