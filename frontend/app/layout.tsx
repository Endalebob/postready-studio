import './globals.css';
import './appearance.css';
export const metadata = { title: 'PostReady Studio', description: 'Your product. Ready to post.' };
const appearanceScript=`(()=>{let choice;try{choice=localStorage.getItem('postready-appearance')}catch{}document.documentElement.dataset.theme=choice==='light'||choice==='dark'?choice:window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'})()`;
export default function Layout({children}:{children:React.ReactNode}) { return <html lang="en" suppressHydrationWarning><head><script id="postready-appearance" dangerouslySetInnerHTML={{__html:appearanceScript}}/></head><body>{children}</body></html>; }
