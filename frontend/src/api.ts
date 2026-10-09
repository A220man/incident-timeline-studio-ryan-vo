import type { User, Incident, Page, Event, Preview, ImportReceipt, Analysis, Advice, History } from './types';
let csrf = '';
export function setCsrf(value:string) { csrf=value; }
export class ApiError extends Error { constructor(public status:number,message:string){super(message);} }
export async function request<T>(path:string, method='GET', body?:unknown):Promise<T> {
 const headers:Record<string,string>={};
 if (method!=='GET') headers['X-CSRF-Token']=csrf;
 if (body!==undefined && !(body instanceof FormData)) headers['Content-Type']='application/json';
 const response=await fetch('/api'+path,{method,credentials:'same-origin',headers,body:body===undefined?undefined:body instanceof FormData?body:JSON.stringify(body)});
 if(response.status===204)return undefined as T;
 const data=await response.json();
 if(!response.ok)throw new ApiError(response.status,data.error?.message ?? (Array.isArray(data.detail)?data.detail.map((item:{msg:string})=>item.msg).join('; '):data.detail) ?? `Request failed (${response.status})`);
 return data as T;
}
const path=(id:string)=>'/incidents/'+encodeURIComponent(id);
export const api={
 mode:()=>request<{mode:string}>('/auth/mode'),
 me:()=>request<User>('/auth/me'),
 demo:()=>request<User>('/auth/demo','POST'),
 logout:()=>request<void>('/auth/logout','POST'),
 list:()=>request<Page<Incident>>('/incidents?limit=200'),
 create:(title:string,description:string)=>request<Incident>('/incidents','POST',{title,description}),
 incident:(id:string)=>request<Incident>(path(id)),
 update:(case_:Incident,status:'open'|'closed')=>request<Incident>(path(case_.id),'PATCH',{title:case_.title,description:case_.description,status,version:case_.version}),
 remove:(id:string)=>request<void>(path(id),'DELETE'),
 events:(id:string,offset:number,query:string,status:string)=>request<Page<Event>>(path(id)+'/events?'+new URLSearchParams({offset:String(offset),limit:'100',query,review_status:status})),
 review:(id:string,event:Event,status:Event['review_status'],note:string)=>request<Event>(path(id)+'/events/'+event.id,'PATCH',{status,note,version:event.version}),
 import:(id:string,file:File,format:string,zone:string,unit:string,commit:boolean)=>{
  const body=new FormData();body.set('file',file);body.set('format',format);body.set('timezone',zone);body.set('epoch_unit',unit);body.set('commit',String(commit));
  return request<Preview|ImportReceipt>(path(id)+'/import','POST',body);
 },
 analysis:(id:string,window:number,gap:number,bucket:number)=>request<Analysis>(path(id)+'/analysis?'+new URLSearchParams({window_seconds:String(window),gap_seconds:String(gap),bucket_seconds:String(bucket)})),
 history:(id:string)=>request<History>(path(id)+'/history'),
 advice:(id:string,external:boolean,window:number,gap:number,bucket:number)=>request<Advice>(path(id)+'/advice','POST',{external,window_seconds:window,gap_seconds:gap,bucket_seconds:bucket}),
 exportUrl:(id:string,format:string)=>'/api'+path(id)+'/export?format='+format,
};
