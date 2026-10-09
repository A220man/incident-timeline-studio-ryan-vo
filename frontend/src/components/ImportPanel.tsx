import { useState } from 'react';
import { api } from '../api';
import type { Preview, ImportReceipt } from '../types';
export function ImportPanel({id,disabled,onImported}:{id:string;disabled:boolean;onImported:()=>void}) {
 const [file,setFile]=useState<File|null>(null),[format,setFormat]=useState('csv'),[zone,setZone]=useState('UTC'),[unit,setUnit]=useState('seconds');
 const [preview,setPreview]=useState<Preview|null>(null),[receipt,setReceipt]=useState<ImportReceipt|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 function reset(){setPreview(null);setReceipt(null);setError('');}
 async function submit(commit:boolean){
  if(!file)return;setBusy(true);setError('');
  try {const result=await api.import(id,file,format,zone,unit,commit);if(commit){setReceipt(result as ImportReceipt);setPreview(null);onImported();}else setPreview(result as Preview);}
  catch(e){setError(String(e));}finally{setBusy(false);}
 }
 return <section className="panel"><h2>Import evidence</h2><p>CSV, JSON array, or JSON Lines · UTF-8 · up to 5 MiB and 10,000 rows. Invalid rows block the whole commit.</p>
  <div className="form-grid"><label>Evidence file<input type="file" accept=".csv,.json,.jsonl,.ndjson" disabled={busy||disabled} onChange={e=>{setFile(e.target.files?.[0]??null);reset();}}/></label>
  <label>Format<select value={format} disabled={busy} onChange={e=>{setFormat(e.target.value);reset();}}><option value="csv">CSV</option><option value="json">JSON array</option><option value="jsonl">JSON Lines</option></select></label>
  <label>Default time zone<input value={zone} disabled={busy} onChange={e=>{setZone(e.target.value);reset();}} placeholder="America/Los_Angeles"/></label>
  <label>Numeric epoch units<select value={unit} disabled={busy} onChange={e=>{setUnit(e.target.value);reset();}}><option value="seconds">Seconds</option><option value="milliseconds">Milliseconds</option></select></label></div>
  <p>Required fields: <code>timestamp</code>, <code>message</code>. Optional: source, severity, actor, host, ip. Explicit offsets override the default zone; ambiguous local times are rejected.</p>
  <div className="actions"><button disabled={!file||busy||disabled} onClick={()=>submit(false)}>Preview import</button><button className="primary" disabled={!preview?.can_commit||busy||disabled} onClick={()=>submit(true)}>Commit evidence</button></div>
  {error&&<p role="alert" className="error">{error}</p>}
  {preview&&<div role="status"><p>{preview.input_rows} input rows · {preview.events.length} unique candidates · {preview.duplicates} repeated rows · {preview.errors.length} errors</p>
   <p className="muted">Existing incident duplicates are checked again at commit. File SHA-256: <code>{preview.upload_sha256}</code></p>
   {preview.errors.length>0&&<ul>{preview.errors.slice(0,20).map(e=><li key={e.row}>Row {e.row}: {e.message}</li>)}</ul>}
   <details><summary>Preview first five events</summary><pre>{JSON.stringify(preview.events.slice(0,5),null,2)}</pre></details></div>}
  {receipt&&<p role="status" className="success">{receipt.replayed?'Previously imported file; no changes.':`Imported ${receipt.inserted} events; skipped ${receipt.duplicates} duplicates.`}</p>}
 </section>;
}
