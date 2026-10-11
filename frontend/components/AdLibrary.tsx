import {useEffect,useState} from 'react';
import {LibraryAd} from '../lib/types';
import {request} from '../lib/api';

function AdThumbnail({ad}:{ad:LibraryAd}){
 const[failed,setFailed]=useState(false);
 return <div className="ad-thumbnail">{failed?<span>Preview unavailable</span>:<img src={'/api/backend/ads/'+ad.id+'/thumbnail?revision='+ad.revision} alt={'Preview of '+ad.product_name} width={120} height={120} loading="lazy" onError={()=>setFailed(true)}/>}</div>
}

export default function AdLibrary({open}:{open:(id:string)=>Promise<void>}){
 const[ads,setAds]=useState<LibraryAd[]>([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[confirm,setConfirm]=useState<string|null>(null),[busy,setBusy]=useState(false);
 async function load(){setLoading(true);setError('');try{setAds(await request<LibraryAd[]>('/ads'))}catch(e){setError(e instanceof Error?e.message:'Could not load your ads.')}finally{setLoading(false)}}
 useEffect(()=>{let active=true;request<LibraryAd[]>('/ads').then(a=>{if(active)setAds(a)}).catch(e=>{if(active)setError(e.message)}).finally(()=>{if(active)setLoading(false)});return()=>{active=false}},[]);
 async function remove(id:string){setBusy(true);setError('');try{await request('/ads/'+id,'DELETE');setAds(a=>a.filter(x=>x.id!==id));setConfirm(null)}catch(e){setError(e instanceof Error?e.message:'Could not delete your ad.')}finally{setBusy(false)}}
 async function choose(id:string){setBusy(true);setError('');try{await open(id)}catch(e){setError(e instanceof Error?e.message:'Could not open your ad.')}finally{setBusy(false)}}
 return <section className="panel"><span className="eyebrow">MY ADS</span><h1>Your recent advertisements.</h1><p>Ads expire seven days after generation. Saving edits keeps the original expiry date.</p>{error&&<p className="error" role="alert">{error}</p>}{loading?<p role="status">Loading your ads…</p>:ads.length===0?<p>No active ads yet. Create an advertisement to get started.</p>:<div className="ad-list">{ads.map(ad=><article className="saved-ad" key={ad.id}><div className="saved-ad-summary"><AdThumbnail key={ad.id+':'+ad.revision} ad={ad}/><div><h2>{ad.product_name}</h2><p>{ad.headline}</p></div></div><p className="contact-help">Expires {new Date(ad.expires_at!).toLocaleString()} · Revision {ad.revision}{!ad.has_png?' · Open and save to prepare PNG':''}</p><div className="actions"><button disabled={busy} onClick={()=>choose(ad.id)}>Open ad</button>{ad.has_png&&<a className="secondary" href={'/api/backend/ads/'+ad.id+'/png'} download>Download saved PNG</a>}<button className="secondary" disabled={busy} onClick={()=>setConfirm(ad.id)}>Delete</button></div>{confirm===ad.id&&<div role="alert"><p>Delete this advertisement? It will no longer be available.</p><button disabled={busy} onClick={()=>remove(ad.id)}>Yes, delete ad</button><button disabled={busy} onClick={()=>setConfirm(null)}>Keep ad</button></div>}</article>)}</div>}<button className="add-contact" disabled={busy||loading} onClick={load}>Refresh ads</button></section>
}
