import { useCallback, useEffect, useState } from 'react';
import { api, ApiError, setCsrf } from './api';
import type { User, Incident, Event, Page, Analysis, Advice, History } from './types';
import { ImportPanel } from './components/ImportPanel';
import { Timeline } from './components/Timeline';
import { AnalysisPanel } from './components/AnalysisPanel';

function Workspace({id,user,onChanged,onDeleted}:{id:string;user:User;onChanged:()=>void;onDeleted:()=>void}) {
 const [case_,setCase]=useState<Incident|null>(null),[events,setEvents]=useState<Page<Event>|null>(null),[report,setReport]=useState<Analysis|null>(null),[history,setHistory]=useState<History|null>(null),[advice,setAdvice]=useState<Advice|null>(null);
 const [revision,setRevision]=useState(0),[offset,setOffset]=useState(0),[query,setQuery]=useState(''),[status,setStatus]=useState('');
 const [window,setWindow]=useState(300),[gap,setGap]=useState(900),[bucket,setBucket]=useState(60),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const canReview=user.roles.includes('admin')||user.roles.includes('reviewer');
 const refresh=()=>{setRevision(n=>n+1);onChanged();};
 useEffect(()=>{let alive=true;Promise.all([api.incident(id),api.analysis(id,window,gap,bucket),api.history(id)]).then(([c,r,h])=>{if(alive){setCase(c);setReport(r);setHistory(h);}}).catch(e=>{if(alive)setError(String(e));});return()=>{alive=false;};},[id,revision,window,gap,bucket]);
 useEffect(()=>{let alive=true;const timer=setTimeout(()=>{api.events(id,offset,query,status).then(result=>{if(alive)setEvents(result);}).catch(e=>{if(alive)setError(String(e));});},150);return()=>{alive=false;clearTimeout(timer);};},[id,revision,offset,query,status]);
 async function changeStatus(){if(!case_)return;setBusy(true);setError('');try{await api.update(case_,case_.status==='open'?'closed':'open');refresh();}catch(e){setError(String(e));}finally{setBusy(false);}}
 async function remove(){if(!confirm('Permanently delete this incident and its imported events? The deletion audit record remains.'))return;setBusy(true);try{await api.remove(id);onDeleted();}catch(e){setError(String(e));}finally{setBusy(false);}}
 async function requestAdvice(external:boolean){setBusy(true);setError('');try{setAdvice(await api.advice(id,external,window,gap,bucket));setRevision(n=>n+1);}catch(e){setError(String(e));}finally{setBusy(false);}}
 if(!case_)return <section className="panel"><p role="status">Loading incident…</p>{error&&<p role="alert" className="error">{error}</p>}</section>;
 return <div className="workspace"><section className="panel hero"><p className="eyebrow">Investigation workspace · {case_.status}</p><h1>{case_.title}</h1><p>{case_.description||'No incident description.'}</p>
  <p className="muted">Created by {case_.created_by} · Revision {case_.version}</p><div className="actions">
   <button onClick={()=>{setError('');refresh();}}>Refresh evidence</button><a className="button" href={api.exportUrl(id,'csv')}>Export CSV</a><a className="button" href={api.exportUrl(id,'json')}>Export JSON</a>
   {canReview&&<button disabled={busy} onClick={changeStatus}>{case_.status==='open'?'Close incident':'Reopen incident'}</button>}
   {user.roles.includes('admin')&&<button className="danger" disabled={busy} onClick={remove}>Delete incident</button>}</div>
   {case_.status==='closed'&&<p>Evidence and decisions are locked while this incident is closed. Reopen it to make changes.</p>}
   {error&&<p role="alert" className="error">{error}</p>}</section>
  <ImportPanel id={id} disabled={!canReview||case_.status==='closed'} onImported={refresh}/>
  <AnalysisPanel report={report} advice={advice} window={window} gap={gap} bucket={bucket} onSettings={(w,g,b)=>{setWindow(w);setGap(g);setBucket(b);setAdvice(null);}} onAdvice={requestAdvice} canReview={canReview} busy={busy}/>
  <Timeline id={id} data={events} offset={offset} onOffset={setOffset} query={query} onQuery={q=>{setQuery(q);setOffset(0);}} status={status} onStatus={s=>{setStatus(s);setOffset(0);}} disabled={!canReview||case_.status==='closed'} onSaved={refresh}/>
  <section className="panel"><h2>Provenance and audit</h2><details><summary>Import receipts ({history?.imports.length??0})</summary>{history?.imports.map(row=><div key={row.id} className="receipt"><strong>{row.created_at}</strong><p>{row.inserted} inserted · {row.duplicates} duplicate rows · by {row.created_by}</p><code>{row.upload_sha256}</code></div>)}</details>
   <details><summary>Latest 200 audit entries</summary>{history?.audit.map(row=><div key={row.id} className="receipt"><strong>{row.action}</strong><p>{row.created_at} · {row.actor}</p><pre>{JSON.stringify(row.detail,null,2)}</pre></div>)}</details></section>
 </div>;
}

export function App(){
 const [user,setUser]=useState<User|null>(null),[mode,setMode]=useState(''),[ready,setReady]=useState(false),[error,setError]=useState('');
 const [incidents,setIncidents]=useState<Incident[]>([]),[selected,setSelected]=useState(''),[title,setTitle]=useState(''),[description,setDescription]=useState(''),[busy,setBusy]=useState(false);
 const load=useCallback(()=>{api.list().then(result=>setIncidents(result.items)).catch(e=>setError(String(e)));},[]);
 function session(value:User){setUser(value);setCsrf(value.csrf_token);}
 useEffect(()=>{api.mode().then(result=>setMode(result.mode)).catch(e=>setError(String(e)));api.me().then(session).catch(e=>{if(!(e instanceof ApiError&&e.status===401))setError(String(e));}).finally(()=>setReady(true));},[]);
 useEffect(()=>{if(user)load();},[user,load]);
 async function demo(){setBusy(true);setError('');try{session(await api.demo());}catch(e){setError(String(e));}finally{setBusy(false);}}
 async function logout(){setBusy(true);try{await api.logout();setUser(null);setCsrf('');setIncidents([]);setSelected('');}catch(e){setError(String(e));}finally{setBusy(false);}}
 async function create(e:React.FormEvent){e.preventDefault();setBusy(true);setError('');try{const item=await api.create(title,description);setSelected(item.id);setTitle('');setDescription('');load();}catch(e){setError(String(e));}finally{setBusy(false);}}
 return <><header className="topbar"><a className="brand" href="/">Incident Timeline <span>Studio</span></a><div className="account">{user&&<><span>{user.username} · {user.roles.join(', ')}</span><button disabled={busy} onClick={logout}>Sign out</button></>}</div></header>
  {error&&<div role="alert" className="global-error">{error}</div>}
  {!ready?<main className="welcome"><p>Checking session…</p></main>:!user?<main className="welcome"><p className="eyebrow">Evidence first. Analyst reviewed.</p><h1>Make an incident timeline you can explain.</h1><p>Normalize timestamps, trace shared entities, inspect telemetry gaps, and preserve the reasons behind each decision.</p>
   {mode==='demo'?<button className="primary" disabled={busy} onClick={demo}>Enter local demo</button>:<a className="button primary" href="/api/auth/login">Sign in with SSO</a>}
   <p className="muted">{mode==='demo'?'Local demo only. Production requires an identity provider.':'Uses your organization’s OIDC provider. SAML can be connected through its broker.'}</p></main>:
   <main className="layout"><aside className="sidebar"><h2>Incidents</h2><p className="muted">Shared analyst workspace</p><div className="incident-list">{incidents.map(item=><button className={selected===item.id?'selected':''} key={item.id} onClick={()=>setSelected(item.id)}><strong>{item.title}</strong><span>{item.status} · {item.event_count??0} events · {item.unreviewed_count??0} unreviewed</span></button>)}{!incidents.length&&<p>No incidents yet.</p>}</div>
    {(user.roles.includes('admin')||user.roles.includes('reviewer'))&&<form onSubmit={create}><h3>New incident</h3><label>Incident title<input value={title} maxLength={200} required onChange={e=>setTitle(e.target.value)}/></label><label>Description<textarea value={description} maxLength={4000} onChange={e=>setDescription(e.target.value)}/></label><button className="primary" disabled={busy||!title.trim()}>Create incident</button></form>}</aside>
    {selected?<Workspace key={selected} id={selected} user={user} onChanged={load} onDeleted={()=>{setSelected('');load();}}/>:<section className="panel empty"><h1>Select or create an incident</h1><p>Import CSV or JSON evidence, review the correlation graph, and record your conclusions. All stored times are normalized to UTC.</p></section>}</main>}
  <footer>Ryan Vo · <a href="mailto:ryandtvo@gmail.com">ryandtvo@gmail.com</a> · <a href="https://github.com/A220man">GitHub</a><span>Correlation is evidence for review, not a verdict.</span></footer></>;
}
