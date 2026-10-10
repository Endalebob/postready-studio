import {Details,Result} from './types';
export async function generate(photo:File,details:Details,includeLogo=true):Promise<Result>{
 const form=new FormData(); form.append('photo',photo);form.append('details',JSON.stringify(details));form.append('include_logo',String(includeLogo));
 const response=await fetch('/api/backend/generate',{method:'POST',headers:{'x-postready':'1'},body:form});
 const data=await response.json().catch(()=>({detail:'Service temporarily unavailable. Please try again.'}));
 if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:Array.isArray(data.detail)?data.detail.map((e:{message?:string;msg?:string})=>e.message||e.msg).join(' '):'We couldn’t create your ad. Please try again.');
 return data;
}

export async function request<T>(path:string,method='GET',body?:unknown):Promise<T>{
 const response=await fetch('/api/backend'+path,{method,headers:{'x-postready':'1',...(body instanceof FormData?{}:body?{'Content-Type':'application/json'}:{})},body:body instanceof FormData?body:body?JSON.stringify(body):undefined});
 const data=await response.json().catch(()=>({detail:'Service temporarily unavailable. Please try again.'}));
 if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:Array.isArray(data.detail)?data.detail.map((e:{msg?:string;message?:string})=>e.msg||e.message).join(' '):'Could not complete the request. Please try again.');
 return data;
}
