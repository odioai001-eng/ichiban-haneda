// 到着・出発通知をバックグラウンド中でもより確実に表示するための最小限のService Worker。
// ネットワークのキャッシュ制御には一切関与しない（fetchイベントを扱わない）ため、
// アプリ更新検知（checkForUpdate）の挙動には影響しない。
self.addEventListener('install',e=>{
  self.skipWaiting();
});
self.addEventListener('activate',e=>{
  e.waitUntil(self.clients.claim());
});
self.addEventListener('notificationclick',e=>{
  e.notification.close();
  e.waitUntil(
    self.clients.matchAll({type:'window',includeUncontrolled:true}).then(clientList=>{
      for(const client of clientList){
        if('focus'in client)return client.focus();
      }
      if(self.clients.openWindow)return self.clients.openWindow('./');
    })
  );
});
