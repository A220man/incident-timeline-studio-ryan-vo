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
export function Timeline({id,data,offset,onOffset,query,onQuery,status,onStatus,disabled,onSaved}:{id:string;data:Page<Event>|null;offset:number;onOffset:(n:number)=>void;query:string;onQuery:(v:string)=>void;status:string;onStatus:(v:string)=>void;disabled:boolean;onSaved:()=>void}) {
 return <section className="panel"><div className="section-heading"><h2>Evidence timeline</h2><span>{data?.total??0} matching events · UTC</span></div>
  <div className="form-grid"><label>Search evidence<input value={query} onChange={e=>onQuery(e.target.value)} placeholder="Message, source, actor or host"/></label><label>Review filter<select aria-label="Review filter" value={status} onChange={e=>onStatus(e.target.value)}><option value="">All decisions</option><option value="unreviewed">Unreviewed</option><option value="relevant">Relevant</option><option value="benign">Benign</option></select></label></div>
  {!data?.items.length&&<p className="empty">No events match. Import evidence or change the filters.</p>}
  <ol className="timeline">{data?.items.map(event=><li key={event.id}><div className="event-heading"><time>{event.timestamp}</time><span className={`badge ${event.severity}`}>{event.severity}</span><span className="badge">{event.review_status}</span></div>
   <strong>{event.source}</strong><p className="message">{event.message}</p><p className="muted">{[event.actor&&`Actor: ${event.actor}`,event.host&&`Host: ${event.host}`,event.ip&&`IP: ${event.ip}`].filter(Boolean).join(' · ')||'No explicit entities'}</p>
   <Decision key={event.version} event={event} id={id} disabled={disabled} onSaved={onSaved}/></li>)}</ol>
  <div className="actions"><button disabled={offset===0} onClick={()=>onOffset(Math.max(0,offset-100))}>Previous 100</button><span>{data?.total?`${offset+1}–${Math.min(offset+100,data.total)} of ${data.total}`:'0 events'}</span><button disabled={!data||offset+100>=data.total} onClick={()=>onOffset(offset+100)}>Next 100</button></div>
 </section>;
}
