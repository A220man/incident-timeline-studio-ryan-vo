import { render,screen,fireEvent } from '@testing-library/react';
import { afterEach,expect,test,vi } from 'vitest';
import { ImportPanel } from '../components/ImportPanel';
import { api } from '../api';
afterEach(()=>vi.restoreAllMocks());
test('invalid preview never enables a commit',async()=>{
 vi.spyOn(api,'import').mockResolvedValue({events:[],errors:[{row:2,message:'Invalid timestamp'}],duplicates:0,input_rows:2,upload_sha256:'synthetic-hash',can_commit:false});
 render(<ImportPanel id="case" disabled={false} onImported={()=>{}}/>);
 fireEvent.change(screen.getByLabelText('Evidence file'),{target:{files:[new File(['bad'],'events.csv')]}});
 fireEvent.click(screen.getByRole('button',{name:'Preview import'}));
 await screen.findByText('Row 2: Invalid timestamp');expect(screen.getByRole('button',{name:'Commit evidence'})).toBeDisabled();
});
test('changing timestamp interpretation invalidates an approved preview',async()=>{
 vi.spyOn(api,'import').mockResolvedValue({events:[],errors:[],duplicates:0,input_rows:1,upload_sha256:'synthetic-hash',can_commit:true});
 render(<ImportPanel id="case" disabled={false} onImported={()=>{}}/>);
 fireEvent.change(screen.getByLabelText('Evidence file'),{target:{files:[new File(['data'],'events.csv')]}});
 fireEvent.click(screen.getByRole('button',{name:'Preview import'}));
 await screen.findByText(/1 input rows/);expect(screen.getByRole('button',{name:'Commit evidence'})).toBeEnabled();
 fireEvent.change(screen.getByLabelText('Default time zone'),{target:{value:'America/Los_Angeles'}});
 expect(screen.getByRole('button',{name:'Commit evidence'})).toBeDisabled();
});
