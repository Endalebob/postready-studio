import {useRef,useState} from 'react';
import {User} from '../lib/types';

const destinations=[
 {id:'home',label:'Overview',mark:'◈'},
 {id:'library',label:'My ads',mark:'▧'},
 {id:'gallery',label:'Campaign gallery',mark:'▦'},
 {id:'video',label:'Video studio',mark:'▷'},
 {id:'social',label:'Social channels',mark:'↗'},
];

export default function AppHeader({user,loading,active,navigate,logout}:{user:User|null;loading:boolean;active:string;navigate:(step:string)=>void;logout:()=>Promise<void>}){
 const[expanded,setExpanded]=useState(false);const account=useRef<HTMLDetailsElement>(null);
 function go(step:string){setExpanded(false);if(account.current)account.current.open=false;navigate(step)}
 return <header className="app-header">
  <div className="header-top">
   <button className="brand" aria-label="PostReady Studio home" onClick={()=>go('home')}><span className="brand-mark">P</span><span className="brand-name">PostReady <strong>Studio</strong></span></button>
   <div className="header-account">
    {loading?<span className="header-loading">Loading…</span>:user?<details ref={account} className="account-menu" key={active} onKeyDown={e=>{if(e.key==='Escape'){e.currentTarget.open=false;e.currentTarget.querySelector('summary')?.focus()}}}>
     <summary aria-label="Account menu"><span className="user-avatar">{user.username.slice(0,1).toUpperCase()}</span><span className="account-label">Your workspace</span><span aria-hidden="true">⌄</span></summary>
     <div className="account-popover"><span className="account-identity">{user.username}</span><button onClick={()=>go('profile')}>Business profile</button><button onClick={()=>{setExpanded(false);void logout()}}>Sign out</button></div>
    </details>:<button className="secondary" onClick={()=>go('account')}>Sign in</button>}
    {user&&<button className="menu-toggle" aria-expanded={expanded} aria-controls="workspace-navigation" onClick={()=>setExpanded(!expanded)}>{expanded?'Close':'Menu'} <span aria-hidden="true">{expanded?'×':'☰'}</span></button>}
   </div>
  </div>
  {user&&<nav id="workspace-navigation" aria-label="Workspace" className={'workspace-nav'+(expanded?' is-open':'')}>
   {destinations.map(item=><button key={item.id} aria-current={active===item.id?'page':undefined} onClick={()=>go(item.id)}><span className="nav-mark" aria-hidden="true">{item.mark}</span>{item.label}</button>)}
   <button className="nav-create" aria-current={['upload','details','generating','result','error'].includes(active)?'page':undefined} onClick={()=>go('create')}><span aria-hidden="true">＋</span> Create ad</button>
  </nav>}
 </header>
}
