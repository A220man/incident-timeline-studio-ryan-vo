export interface User { subject:string; username:string; roles:string[]; csrf_token:string }
export interface Incident { id:string; title:string; description:string; status:'open'|'closed'; version:number; created_by:string; created_at:string; updated_at:string; event_count?:number; unreviewed_count?:number }
export interface Event { id:string; incident_id:string; import_id:string; timestamp:string; original_timestamp:string; source:string; message:string; severity:string; actor:string; host:string; ip:string; fingerprint:string; raw_sha256:string; row_number:number; review_status:'unreviewed'|'relevant'|'benign'; review_note:string; reviewed_by:string; version:number }
export interface Page<T> { items:T[]; total:number; limit?:number; offset?:number }
export interface Preview { events:Partial<Event>[]; errors:{row:number;message:string}[]; duplicates:number; input_rows:number; upload_sha256:string; can_commit:boolean }
export interface ImportReceipt { id:string; inserted:number; duplicates:number; input_rows:number; replayed:boolean; upload_sha256:string; created_at:string; created_by:string }
export interface Analysis {
 event_count:number; entities:{type:string;value:string;event_ids:string[];sources:string[];count:number}[];
 correlation:{components:{event_ids:string[];size:number;start:string;end:string;sources:string[];duration_seconds:number}[]; edges:{from:string;to:string;entity_type:string;entity:string;delta_seconds:number}[];isolated_events:number;window_seconds:number};
 gaps:{source:string;start:string;end:string;seconds:number;before_event_id:string;after_event_id:string}[];
 rates:{buckets:{start:string;count:number;score:number;anomalous:boolean}[];anomalies:{start:string;count:number;score:number}[];method:string;baseline:{median:number;mad:number;scale:number;bucket_seconds:number;z_threshold:number;sample_size:number}|null;message?:string};
 limitations:string[];
}
export interface Advice { mode:'local'|'external';items:{evidence:string;action:string}[];evidence:Record<string,unknown>;limitations:string;warning?:string }
export interface History { imports:ImportReceipt[];audit:{id:number;actor:string;action:string;target:string;detail:Record<string,unknown>;created_at:string}[] }
