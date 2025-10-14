let db;
export async function initDB(){
  return new Promise((resolve,reject)=>{
    const req = indexedDB.open('av_ai_ops', 2);
    req.onupgradeneeded = (e)=>{
      const d = e.target.result;
      if (!d.objectStoreNames.contains('config')) d.createObjectStore('config',{keyPath:'id'});
      if (!d.objectStoreNames.contains('recipes')) d.createObjectStore('recipes',{keyPath:'id'});
      if (!d.objectStoreNames.contains('experiments')) d.createObjectStore('experiments',{keyPath:'id'});
      if (!d.objectStoreNames.contains('outcomes')) d.createObjectStore('outcomes',{keyPath:'id'});
      if (!d.objectStoreNames.contains('logs')) d.createObjectStore('logs',{keyPath:'id'});
      if (!d.objectStoreNames.contains('telemetry')) d.createObjectStore('telemetry',{keyPath:'id'});
      if (!d.objectStoreNames.contains('health')) d.createObjectStore('health',{keyPath:'id'});
    };
    req.onsuccess=()=>{ db=req.result; resolve(); };
    req.onerror=()=>reject(req.error);
  });
}
export async function ensureStores(){
  if (db) return;
  await new Promise((res,rej)=>{
    const req = indexedDB.open('av_ai_ops'); req.onsuccess=()=>{db=req.result;res();}; req.onerror=()=>rej(req.error);
  });
}
export async function put(store, obj){
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(store,'readwrite'); tx.objectStore(store).put(obj);
    tx.oncomplete=()=>resolve(true); tx.onerror=()=>reject(tx.error);
  });
}
export async function get(store, id){
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(store,'readonly'); const r=tx.objectStore(store).get(id);
    r.onsuccess=()=>resolve(r.result); r.onerror=()=>reject(r.error);
  });
}
export async function all(store){
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(store,'readonly'); const r=tx.objectStore(store).getAll();
    r.onsuccess=()=>resolve(r.result||[]); r.onerror=()=>reject(r.error);
  });
}