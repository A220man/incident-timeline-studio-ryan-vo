import type { Analysis, Advice } from '../types';
export function AnalysisPanel({report,advice,window,gap,bucket,onSettings,onAdvice,canReview,busy}:{report:Analysis|null;advice:Advice|null;window:number;gap:number;bucket:number;onSettings:(a:number,b:number,c:number)=>void;onAdvice:(external:boolean)=>void;canReview:boolean;busy:boolean}) {
 return <section className="panel"><h2>Correlation and coverage</h2><p>Connections are investigation leads. They do not establish causality or compromise.</p>
  <form className="form-grid" onSubmit={e=>{e.preventDefault();const data=new FormData(e.currentTarget);onSettings(Number(data.get('window')),Number(data.get('gap')),Number(data.get('bucket')));}}>
   <label>Entity window (seconds)<input name="window" type="number" min="1" max="86400" defaultValue={window} required/></label>
   <label>Gap threshold (seconds)<input name="gap" type="number" min="1" max="604800" defaultValue={gap} required/></label>
   <label>Rate bucket (seconds)<input name="bucket" type="number" min="1" max="86400" defaultValue={bucket} required/></label><button type="submit" disabled={busy}>Recalculate</button></form>
  {report&&<><div className="metrics"><div><strong>{report.event_count}</strong><span>events</span></div><div><strong>{report.correlation.components.length}</strong><span>components</span></div><div><strong>{report.gaps.length}</strong><span>observed gaps</span></div><div><strong>{report.rates.anomalies.length}</strong><span>rate alerts</span></div></div>
   <details open><summary>Temporal links ({report.correlation.edges.length})</summary><p className="muted">Adjacent appearances of a shared entity within {report.correlation.window_seconds}s form edges. Components may span longer through a chain.</p>
    <div className="table-scroll"><table><thead><tr><th>Shared entity</th><th>Type</th><th>Δ seconds</th><th>Event pair</th></tr></thead><tbody>{report.correlation.edges.slice(0,100).map((edge,i)=><tr key={i}><td>{edge.entity}</td><td>{edge.entity_type}</td><td>{edge.delta_seconds}</td><td><code>{edge.from.slice(0,8)} → {edge.to.slice(0,8)}</code></td></tr>)}</tbody></table></div>
    {report.correlation.edges.length>100&&<p>Showing first 100 links. Export JSON for the full graph.</p>}</details>
   <details><summary>Entity inventory ({report.entities.length})</summary><div className="table-scroll"><table><thead><tr><th>Entity</th><th>Type</th><th>Events</th><th>Sources</th></tr></thead><tbody>{report.entities.slice(0,100).map(row=><tr key={row.type+row.value}><td>{row.value}</td><td>{row.type}</td><td>{row.count}</td><td>{row.sources.join(', ')}</td></tr>)}</tbody></table></div></details>
   <details><summary>Coverage gaps ({report.gaps.length})</summary>{report.gaps.slice(0,100).map((row,i)=><p key={i}><strong>{row.source}</strong>: {row.seconds}s between {row.start} and {row.end}</p>)}<p className="muted">Only internal gaps between supplied events are reported. No collector-health claim is made.</p></details>
   <details><summary>Event-rate analysis · {report.rates.method.replaceAll('_',' ')}</summary>{report.rates.message&&<p>{report.rates.message}</p>}
    {report.rates.baseline&&<p>Median {report.rates.baseline.median} · MAD {report.rates.baseline.mad} · {report.rates.baseline.sample_size} buckets</p>}
    <div className="table-scroll"><table><thead><tr><th>Bucket start (UTC)</th><th>Events</th><th>Score</th></tr></thead><tbody>{report.rates.anomalies.slice(0,100).map(row=><tr key={row.start}><td>{row.start}</td><td>{row.count}</td><td>{row.score}</td></tr>)}</tbody></table></div></details>
   <ul className="muted">{report.limitations.map(line=><li key={line}>{line}</li>)}</ul></>}
  <h3>Investigation advice</h3><p>External advice sends aggregate counts and timing statistics only. Raw events, entity values and analyst notes stay on this server.</p>
  <div className="actions"><button disabled={!canReview||busy} onClick={()=>onAdvice(false)}>Local advice</button><button disabled={!canReview||busy} onClick={()=>onAdvice(true)}>Request external advice</button></div>
  {advice&&<div><p className="badge">{advice.mode==='local'?'Local deterministic guidance':'External model guidance'}</p>{advice.warning&&<p role="status">{advice.warning}</p>}
   <ul>{advice.items.map((item,i)=><li key={i}><strong>{item.evidence}:</strong> {item.action}</li>)}</ul><p className="muted">{advice.limitations}</p></div>}
 </section>;
}
