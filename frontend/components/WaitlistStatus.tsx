import {useState} from 'react';
import {User} from '../lib/types';

export default function WaitlistStatus({user,refresh}:{user:User;refresh:()=>Promise<void>}){
 const[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function check(){setBusy(true);setError('');try{await refresh()}catch(e){setError(e instanceof Error?e.message:'Could not check your access. Please try again.')}finally{setBusy(false)}}
 return <section className="panel waitlist-status"><span className="eyebrow">POSTREADY PRIVATE PREVIEW</span><div className="waitlist-symbol" aria-hidden="true">◷</div><h1>{user.access_status==='suspended'?'Your access is paused.':'You’re on the waitlist.'}</h1><p>{user.access_status==='suspended'?'Your account is saved. An administrator needs to approve access before you can use the workspace again.':'Thanks for joining. We’re welcoming a small group of business owners while we refine PostReady Studio.'}</p><div className="waitlist-details"><h2>What happens next?</h2><p>An administrator will review your request. If approved, you’ll receive limited access to create image advertisements.</p><p>Sign in later or check your status here. Your workspace opens after approval.</p></div>{error&&<p className="error" role="alert">{error}</p>}<button className="primary" disabled={busy} onClick={check}>{busy?'Checking…':'Check access status'}</button></section>
}
