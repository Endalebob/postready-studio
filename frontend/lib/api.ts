import {Details,Result} from './types';
export async function generate(photo:File,details:Details):Promise<Result>{
 const form=new FormData(); form.append('photo',photo);form.append('details',JSON.stringify(details));
 const response=await fetch('/api/backend/generate',{method:'POST',body:form});
 const data=await response.json();
 if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:Array.isArray(data.detail)?data.detail.map((e:{message?:string;msg?:string})=>e.message||e.msg).join(' '):'We couldn’t create your ad. Please try again.');
 return data;
}
