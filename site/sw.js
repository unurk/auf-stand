const CACHE = 'auf-stand-v2';
const SHELL = ['./', './index.html', './dossier.html', './archiv/index.html',
  './icon-192.png', './icon-512.png', './apple-touch-icon.png'];

self.addEventListener('install', function(e){
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(function(c){
    return Promise.all(SHELL.map(function(u){ return c.add(u).catch(function(){}); }));
  }));
});

self.addEventListener('activate', function(e){
  e.waitUntil(caches.keys().then(function(keys){
    return Promise.all(keys.filter(function(k){ return k !== CACHE; })
      .map(function(k){ return caches.delete(k); }));
  }).then(function(){ return self.clients.claim(); }));
});

self.addEventListener('fetch', function(e){
  var req = e.request;
  if(req.method !== 'GET') return;
  var url = new URL(req.url);
  if(url.origin !== self.location.origin){
    // Fremd-Assets (Google Fonts): cache-first, lange haltbar.
    e.respondWith(caches.open(CACHE).then(function(c){
      return c.match(req).then(function(hit){
        return hit || fetch(req).then(function(res){
          try { c.put(req, res.clone()); } catch(err){}
          return res;
        }).catch(function(){ return hit; });
      });
    }));
    return;
  }
  // Eigene Seiten: network-first, Cache als Offline-Fallback.
  e.respondWith(fetch(req).then(function(res){
    if(res && res.ok){
      var copy = res.clone();
      caches.open(CACHE).then(function(c){ c.put(req, copy); });
    }
    return res;
  }).catch(function(){
    return caches.match(req).then(function(hit){
      return hit || caches.match('./index.html');
    });
  }));
});

// Web-Push: Notification anzeigen und bei Klick die PWA öffnen.
self.addEventListener('push', function(e){
  var d = {};
  try { d = e.data.json(); } catch(err){}
  e.waitUntil(self.registration.showNotification(d.title || 'Auf Stand', {
    body: d.body || '', icon: './icon-192.png', badge: './icon-192.png',
    data: { url: d.url || './index.html' }, tag: 'lagebild'
  }));
});

self.addEventListener('notificationclick', function(e){
  e.notification.close();
  var target = (e.notification.data && e.notification.data.url) || './index.html';
  e.waitUntil(clients.matchAll({type:'window'}).then(function(list){
    for(var i=0;i<list.length;i++){ if('focus' in list[i]) return list[i].focus(); }
    if(clients.openWindow) return clients.openWindow(target);
  }));
});
