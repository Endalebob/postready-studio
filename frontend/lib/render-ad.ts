import {Result} from './types';
import {themes} from './themes';
function text(ctx:CanvasRenderingContext2D,value:string,y:number,maxLines:number,size:number,color='#252e28'){
 const words=value.split(/\s+/); let lines:string[]=[];
 for(let font=size;font>=22;font-=2){ctx.font=`${font}px Ethiopic, Arial, sans-serif`;lines=[];let line='';
  for(const word of words){const next=line?`${line} ${word}`:word;if(ctx.measureText(next).width>940&&line){lines.push(line);line=word;}else line=next;}
  if(line)lines.push(line);
  if(lines.length<=maxLines&&lines.every(l=>ctx.measureText(l).width<=940)){ctx.fillStyle=color;lines.forEach((l,i)=>ctx.fillText(l,70,y+i*(font+9)));return;}
 }
 throw new Error('This text is too long for your ad. Please shorten it.');
}
export async function renderAd(canvas:HTMLCanvasElement,r:Result){
 await document.fonts.load('32px Ethiopic'); await document.fonts.ready;
 const image=new Image();image.src=`data:${r.artwork.mime_type};base64,${r.artwork.base64}`;await image.decode();
 canvas.width=1080;canvas.height=1080;const c=canvas.getContext('2d')!;const theme=themes[r.details.theme||'ethiopian-warmth'];
 c.fillStyle=theme.background;c.fillRect(0,0,1080,1080);
 const scale=Math.min(980/image.width,575/image.height);const w=image.width*scale,h=image.height*scale;c.drawImage(image,(1080-w)/2,30+(575-h)/2,w,h);
 c.fillStyle=theme.price;c.fillRect(40,620,1000,4);
 text(c,r.image_text.headline,684,2,46,r.details.theme==='bold-contrast'?theme.price:theme.text);text(c,r.image_text.tagline,804,2,28,theme.text);
 const am=r.details.language==='am'; const price=`${r.details.current_price} ${am?'ብር':'ETB'}`;
 text(c,price+(r.details.old_price?` · ${am?'ቅናሽ':'Save'} ${r.discount_percent}% (${r.details.old_price})`:''),875,1,34,theme.price);
 if(r.details.address)text(c,r.details.address,923,1,24,theme.text);
 r.details.contacts.forEach((contact,index)=>text(c,`${contact.kind}: ${contact.value}`,960+index*25,1,22,theme.contact));
 for(let x=40;x<1040;x+=24){c.fillStyle=x%48===40?theme.accent:theme.price;c.fillRect(x,1042,14,8);}
}
