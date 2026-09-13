const CACHE='rw-20260914';
const URLS=["./", "./index.html", "./kratisi.html", "./melos.html", "./eukairia.html", "./faq.html", "./epikoinonia.html", "./nomika.html", "./manifest.json"];
self.addEventListener('install',e=>{
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(URLS)));
  self.skipWaiting();
});
self.addEventListener('activate',e=>{
  e.waitUntil(caches.keys().then(ks=>Promise.all(
    ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  e.respondWith(caches.open(CACHE).then(cache=>{
    return cache.match(e.request).then(hit=>{
      const net=fetch(e.request).then(r=>{if(r.status===200)cache.put(e.request,r.clone());return r;}).catch(()=>hit);
      return hit||net;
    });
  }));
});
