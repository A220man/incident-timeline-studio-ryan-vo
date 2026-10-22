import { useState } from 'react';
import { api } from '../api';
import type { Event, Page } from '../types';

function Decision({event,id,disabled,onSaved}:{event:Event;id:string;disabled:boolean;onSaved:()=>void}) {
 const [status,setStatus]=useState(event.review_status),[note,setNote]=useState(event.review_note),[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function save(){setBusy(true);setError('');try{await api.review(id,event,status,note);onSaved();}catch(e){setError(String(e));}finally{setBusy(false);}}
 return <details><summary>Review decision and provenance</summary><div className="form-grid"><label>Decision<select aria-label="Decision" value={status} disabled={disabled} onChange={e=>setStatus(e.target.value as Event['review_status'])}><option value="unreviewed">Unreviewed</option><option value="relevant">Relevant</option><option value="benign">Benign</option></select></label>
  <label>Analyst note<textarea value={note} maxLength={4000} disabled={disabled} onChange={e=>setNote(e.target.value)}/></label></div>
  <button onClick={save} disabled={busy||disabled}>Save decision</button>{error&&<p role="alert" className="error">{error}</p>}
  <dl><dt>Original timestamp</dt><dd>{event.original_timestamp}</dd><dt>Import row</dt><dd>{event.row_number}</dd><dt>Raw row SHA-256</dt><dd><code>{event.raw_sha256}</code></dd><dt>Normalized fingerprint</dt><dd><code>{event.fingerprint}</code></dd><dt>Reviewed by</dt><dd>{event.reviewed_by||'Not reviewed'}</dd></dl></details>;
}

function BulkActionBar({id,selectedIds,disabled,onSaved,totalFiltered}:{id:string;selectedIds:string[];disabled:boolean;onSaved:()=>void;totalFiltered:number}) {
 const [status,setStatus]=useState<Event['review_status']>('relevant');
 const [note,setNote]=useState('');
 const [tags,setTags]=useState('');
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [success,setSuccess]=useState('');
 async function apply(){
  if(!selectedIds.length)return;
  setBusy(true);setError('');setSuccess('');
  try{
   const tagList=tags.split(',').map(t=>t.trim()).filter(Boolean);
   await api.bulkReview(id,selectedIds,status,note,tagList);
   setSuccess(`Updated ${selectedIds.length} event(s)`);
   onSaved();
  }catch(e){setError(String(e));}
  finally{setBusy(false);}
 }

 if(!selectedIds.length)return null;
 return <div className="bulk-bar" role="status" aria-live="polite">
  <strong>Bulk action for {selectedIds.length} of {totalFiltered} filtered event(s):</strong>
  <div className="form-grid">
   <label>Decision<select aria-label="Bulk decision" value={status} disabled={disabled||busy} onChange={e=>setStatus(e.target.value as Event['review_status'])}><option value="unreviewed">Unreviewed</option><option value="relevant">Relevant</option><option value="benign">Benign</option></select></label>
   <label>Note<textarea value={note} maxLength={4000} disabled={disabled||busy} onChange={e=>setNote(e.target.value)} placeholder="Shared note for all selected events"/></label>
   <label>Tags (comma-separated)<input value={tags} disabled={disabled||busy} onChange={e=>setTags(e.target.value)} placeholder="phishing, credential-access" maxLength={512}/></label>
  </div>
  <div className="actions">
   <button className="primary" disabled={disabled||busy} onClick={apply}>{busy?'Applying…':`Apply to ${selectedIds.length} event(s)`}</button>
   <button disabled={busy} onClick={()=>onSaved()}>Clear selection</button>
  </div>
  {error&&<p className="error">{error}</p>}
  {success&&<p className="success">{success}</p>}
 </div>;
}

export function Timeline({id,data,offset,onOffset,query,onQuery,status,onStatus,severity,onSeverity,component,onComponent,components,disabled,onSaved}:{id:string;data:Page<Event>|null;offset:number;onOffset:(n:number)=>void;query:string;onQuery:(v:string)=>void;status:string;onStatus:(v:string)=>void;severity:string;onSeverity:(v:string)=>void;component:string;onComponent:(v:string)=>void;components:{component_id:string;size:number;start:string;end:string;duration_seconds:number}[];disabled:boolean;onSaved:()=>void}) {
 const [selectedIds,setSelectedIds]=useState<string[]>([]);
 const totalFiltered=data?.total??0;
 const toggleSelect=(eventId:string)=>setSelectedIds(prev=>prev.includes(eventId)?prev.filter(id=>id!==eventId):[...prev,eventId]);
 const selectAll=()=>setSelectedIds(data?.items.map(e=>e.id)||[]);
 const clearSelection=()=>{setSelectedIds([]);onSaved();};

 return <section className="panel">
  <div className="section-heading"><h2>Evidence timeline</h2><span>{totalFiltered} matching events · UTC</span></div>
  <div className="form-grid"><label>Search evidence<input value={query} onChange={e=>onQuery(e.target.value)} placeholder="Message, source, actor or host"/></label>
   <label>Review filter<select aria-label="Review filter" value={status} onChange={e=>onStatus(e.target.value)}><option value="">All decisions</option><option value="unreviewed">Unreviewed</option><option value="relevant">Relevant</option><option value="benign">Benign</option></select></label>
   <label>Severity filter<select aria-label="Severity filter" value={severity} onChange={e=>onSeverity(e.target.value)}><option value="">All severities</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option><option value="info">Info</option><option value="debug">Debug</option><option value="unknown">Unknown</option></select></label>
   <label>Component filter<select aria-label="Component filter" value={component} onChange={e=>onComponent(e.target.value)}><option value="">All components</option>{components.map(c=><option key={c.component_id} value={c.component_id}>Component {c.component_id.slice(0,8)} ({c.size} events, {c.duration_seconds}s)</option>)}</select></label></div>
  {!data?.items.length&&<p className="empty">No events match. Import evidence or change the filters.</p>}
  <BulkActionBar id={id} selectedIds={selectedIds} disabled={disabled} onSaved={clearSelection} totalFiltered={totalFiltered}/>
  <ol className="timeline">{data?.items.map(event=><li key={event.id}><label className="event-row"><input type="checkbox" checked={selectedIds.includes(event.id)} onChange={()=>toggleSelect(event.id)} aria-label={`Select event ${event.id}`} disabled={disabled}/><div className="event-content"><div className="event-heading"><time>{event.timestamp}</time><span className={`badge ${event.severity}`}>{event.severity}</span><span className="badge">{event.review_status}</span></div>
   <strong>{event.source}</strong><p className="message">{event.message}</p><p className="muted">{[event.actor&&`Actor: ${event.actor}`,event.host&&`Host: ${event.host}`,event.ip&&`IP: ${event.ip}`].filter(Boolean).join(' · ')||'No explicit entities'}</p>
   <Decision key={event.version} event={event} id={id} disabled={disabled} onSaved={onSaved}/></div></label></li>)}</ol>
  <div className="actions"><button disabled={offset===0} onClick={()=>onOffset(Math.max(0,offset-100))}>Previous 100</button><span>{data?.total?`${offset+1}–${Math.min(offset+100,data.total)} of ${data.total}`:'0 events'}</span><button disabled={!data||offset+100>=data.total} onClick={()=>onOffset(offset+100)}>Next 100</button></div>
 </section>;
}