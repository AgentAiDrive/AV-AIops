let db;
export async function initDB(){
  return new Promise((resolve,reject)=>{
    const req = indexedDB.open('av_ai_ops',1);
    req.onupgradeneeded = (e)=>{
      const d = e.target.result;
      d.createObjectStore('config',{keyPath:'id'});
      d.createObjectStore('recipes',{keyPath:'id'});
      d.createObjectStore('experiments',{keyPath:'id'});
      d.createObjectStore('outcomes',{keyPath:'id'});
      d.createObjectStore('logs',{keyPath:'id'});
    };
    req.onsuccess=()=>{db=req.result;resolve();};
    req.onerror=()=>reject(req.error);
  });
}
export async function put(store, obj){ return new Promise((resolve,reject)=>{ const tx=db.transaction(store,'readwrite'); tx.objectStore(store).put(obj); tx.oncomplete=()=>resolve(true); tx.onerror=()=>reject(tx.error); }); }
export async function get(store, id){ return new Promise((resolve,reject)=>{ const tx=db.transaction(store,'readonly'); const r=tx.objectStore(store).get(id); r.onsuccess=()=>resolve(r.result); r.onerror=()=>reject(r.error); }); }
export async function all(store){ return new Promise((resolve,reject)=>{ const tx=db.transaction(store,'readonly'); const r=tx.objectStore(store).getAll(); r.onsuccess=()=>resolve(r.result||[]); r.onerror=()=>reject(r.error); }); }
