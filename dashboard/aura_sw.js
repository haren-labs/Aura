// Service worker di Aura: serve al telefono per installarla come app.
// Non salva niente in memoria: la pagina arriva sempre fresca dal PC.
// Solo se il PC non risponde, mostra una schermata "Aura non raggiungibile".
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

const OFFLINE = `<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="theme-color" content="#01050c">
<title>Aura</title><style>
body{margin:0;height:100vh;display:grid;place-items:center;background:#01050c;color:#7df9ff;
font-family:monospace;text-align:center;letter-spacing:2px;padding:24px;box-sizing:border-box}
h1{color:#00f5ff;letter-spacing:10px;text-shadow:0 0 14px #00f5ff;font-size:28px}
p{opacity:.8;line-height:1.7;font-size:13px}button{margin-top:18px;padding:12px 22px;background:transparent;
border:1px solid #00f5ff;color:#00f5ff;font-family:monospace;letter-spacing:3px;font-size:13px}
</style></head><body><div><h1>AURA</h1><p>NON RAGGIUNGIBILE<br><br>Il PC e' acceso?<br>Tailscale e' attivo sul telefono?</p>
<button onclick="location.reload()">RIPROVA</button></div></body></html>`;

self.addEventListener('fetch', e => {
  if (e.request.mode !== 'navigate') return;   // le richieste ad Aura (chat, voce...) passano normali
  e.respondWith(fetch(e.request).catch(() =>
    new Response(OFFLINE, { headers: { 'Content-Type': 'text/html; charset=utf-8' } })));
});
