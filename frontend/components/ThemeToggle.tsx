'use client';
import {useEffect,useRef,useState} from 'react';

const preferenceKey='postready-appearance';
type Appearance='light'|'dark';

export default function ThemeToggle(){
 const[theme,setTheme]=useState<Appearance>('light');
 const manual=useRef(false);
 function apply(next:Appearance){document.documentElement.dataset.theme=next;setTheme(next)}
 useEffect(()=>{
  setTheme(document.documentElement.dataset.theme==='dark'?'dark':'light');
  try{manual.current=['light','dark'].includes(localStorage.getItem(preferenceKey)||'')}catch{}
  const media=window.matchMedia('(prefers-color-scheme: dark)');
  const followSystem=()=>{if(!manual.current)apply(media.matches?'dark':'light')};
  const sync=(event:StorageEvent)=>{if(event.key!==preferenceKey&&event.key!==null)return;manual.current=event.newValue==='light'||event.newValue==='dark';apply(manual.current?event.newValue as Appearance:media.matches?'dark':'light')};
  media.addEventListener('change',followSystem);window.addEventListener('storage',sync);
  return()=>{media.removeEventListener('change',followSystem);window.removeEventListener('storage',sync)};
 },[]);
 function toggle(){const next=theme==='dark'?'light':'dark';manual.current=true;apply(next);try{localStorage.setItem(preferenceKey,next)}catch{}}
 const label=theme==='dark'?'Switch to light mode':'Switch to dark mode';
 return <button className="theme-toggle" onClick={toggle} aria-label={label} title={label} aria-pressed={theme==='dark'}>
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{theme==='dark'?<><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.4 1.4m11.2 11.2L19 19M5 19l1.4-1.4M17.6 6.4L19 5"/></>:<path d="M20.5 13.2A8.6 8.6 0 0 1 10.8 3.5a8.6 8.6 0 1 0 9.7 9.7Z"/>}</svg>
  <span className="theme-toggle-label">{theme==='dark'?'Light mode':'Dark mode'}</span>
 </button>
}
