// Network-first for same-origin GETs (updates arrive promptly), cache fallback when offline.
const C='chefmomo-v17';const F=['./','index.html','manifest.webmanifest','icon-180.png','icon-192.png','icon-512.png','icon-maskable-192.png','icon-maskable-512.png','icon.svg','logo.svg','favicon.ico','favicon-32.png','specials/index.json'];
self.addEventListener('install',e=>{self.skipWaiting();e.waitUntil(caches.open(C).then(c=>c.addAll(F)).catch(()=>{}))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{const r=e.request;if(r.method!=='GET')return;const u=new URL(r.url);if(u.origin!==location.origin)return;
  const key=r.mode==='navigate'?'./':r;
  e.respondWith(fetch(r).then(n=>{if(n&&n.ok&&n.type==='basic'&&!n.redirected){const cp=n.clone();caches.open(C).then(c=>c.put(key,cp)).catch(()=>{})}return n})
    .catch(()=>caches.match(key).then(m=>m||caches.match(r,{ignoreSearch:true})).then(m=>m||new Response('Offline',{status:503,headers:{'Content-Type':'text/plain'}}))))});
