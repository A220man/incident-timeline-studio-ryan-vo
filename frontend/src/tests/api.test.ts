import { afterEach, expect, test, vi } from 'vitest';
import { api, setCsrf } from '../api';
afterEach(()=>{vi.unstubAllGlobals();setCsrf('');});
test('sends session CSRF for mutations and preserves credentials policy',async()=>{
 const mock=vi.fn().mockResolvedValue(new Response(JSON.stringify({id:'incident'})));vi.stubGlobal('fetch',mock);setCsrf('synthetic');
 await api.create('Title','Description');expect(mock.mock.calls[0][1].headers['X-CSRF-Token']).toBe('synthetic');expect(mock.mock.calls[0][1].credentials).toBe('same-origin');
});
test('multipart upload does not set a JSON content type',async()=>{
 const mock=vi.fn().mockResolvedValue(new Response(JSON.stringify({can_commit:true})));vi.stubGlobal('fetch',mock);
 await api.import('case',new File(['a,b'],'events.csv'),'csv','UTC','seconds',false);
 expect(mock.mock.calls[0][1].body).toBeInstanceOf(FormData);expect(mock.mock.calls[0][1].headers['Content-Type']).toBeUndefined();
});
test('preserves version conflict detail',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({error:{message:'Refresh before saving'}}),{status:409})));
 await expect(api.create('x','')).rejects.toThrow('Refresh before saving');
});
test('logout handles empty success response',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(null,{status:204})));await expect(api.logout()).resolves.toBeUndefined();
});
