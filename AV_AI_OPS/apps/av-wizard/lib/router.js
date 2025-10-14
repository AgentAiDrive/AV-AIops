// apps/av-wizard/lib/router.js
export function route(routes) {
  const el = document.getElementById('app');
  const current = location.hash;
  const key = (current && routes[current]) ? current : '#/welcome';

  try {
    const View = routes[key];
    const node = View();
    // render safely
    el.innerHTML = '';
    if (node instanceof HTMLElement) el.appendChild(node);
    else el.textContent = String(node ?? '');
  } catch (err) {
    console.error('[router] render failed:', err);
    el.innerHTML = `<pre style="white-space:pre-wrap">Router error: ${err?.message || err}</pre>`;
  }
}
