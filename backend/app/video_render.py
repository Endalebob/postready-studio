"""Deterministic product-photo composition. No paid provider calls."""
import io
import json
import subprocess
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

WIDTH, HEIGHT, FPS = 720, 1280, 24
THEMES = {
    'ethiopian-warmth': ('#f6f2e7', '#252e28', '#326348', '#252e28', '#b08b3b'),
    'bold-contrast': ('#121212', '#ffffff', '#78e895', '#ff8585', '#78e895'),
    'clean-modern': ('#ffffff', '#252e28', '#245fb5', '#245fb5', '#b9c4d2'),
}

def font(size, char):
    ethiopic = 0x1200 <= ord(char) <= 0x139f or 0x2d80 <= ord(char) <= 0x2ddf or 0xab00 <= ord(char) <= 0xab2f
    return loaded_font(size,ethiopic)

@lru_cache(maxsize=96)
def loaded_font(size,ethiopic):
    path = Path(__file__).parent.parent / 'assets/fonts/NotoSansEthiopic.ttf' if ethiopic else Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    return ImageFont.truetype(str(path), size)

def width(text, size):
    return sum(font(size, c).getlength(c) for c in text)

def lines(text, size, max_width):
    result, current = [], ''
    for word in text.split():
        candidate = (current+' '+word).strip()
        if width(candidate,size) <= max_width:
            current = candidate
        else:
            if current:
                result.append(current)
            current = ''
            for c in word:
                if current and width(current+c,size)>max_width:
                    result.append(current); current=''
                current += c
    if current:
        result.append(current)
    return result

def label(draw, text, xy, color, size=28, max_width=620, max_lines=2):
    for chosen in range(size, 11, -1):
        rows = lines(text, chosen, max_width)
        if len(rows) <= max_lines:
            break
    else:
        raise ValueError('Text cannot fit in the video. Shorten the product details.')
    x,y = xy
    for row in rows:
        cursor=x
        for c in row:
            f=font(chosen,c)
            draw.text((cursor,y),c,font=f,fill=color)
            cursor += f.getlength(c)
        y += chosen+8
    return y

def scene(photo, product, settings, destination, logo=None):
    background, text, price, contact, accent = THEMES[settings['theme']]
    canvas=Image.new('RGB',(WIDTH,HEIGHT),background)
    draw=ImageDraw.Draw(canvas)
    business=settings.get('business_name','')
    label(draw,business,(48,42),price,30,480 if logo else 624,2)
    if logo:
        with Image.open(io.BytesIO(logo)) as image:
            image=image.convert('RGBA'); image.thumbnail((100,75))
            canvas.paste(image,(WIDTH-48-image.width,42),image)
    with Image.open(io.BytesIO(photo)) as image:
        image=ImageOps.contain(image.convert('RGB'),(624,650))
        canvas.paste(image,((WIDTH-image.width)//2,150+(650-image.height)//2))
    draw.line((48,820,672,820),fill=price,width=3)
    label(draw,product['name'],(48,845),text,38,624,2)
    if product.get('price'):
        label(draw,product['price']+' '+('ብር' if settings['language']=='am' else 'ETB'),(48,953),price,32,624,1)
    label(draw,product.get('description',''),(48,1004),text,23,624,3)
    for i,item in enumerate(settings.get('contacts',[])):
        label(draw,item['kind']+': '+item['value'],(48+(i%2)*320,1114+(i//2)*49),contact,18,300,2)
    label(draw,settings.get('address',''),(48,1220),text,17,624,2)
    for x in range(48,672,24):
        draw.rectangle((x,1266,x+13,1271),fill=price if (x//24)%2 else accent)
    canvas.save(destination,format='PNG')

def command(args, timeout=180):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
    if result.returncode:
        # Provider credentials/user text are never placed in errors or command strings.
        raise RuntimeError('Video processing could not complete.')
    return result.stdout

def render(photos, products, settings, directory, logo=None):
    root=Path(directory)
    paths=[]
    for i,(photo,product) in enumerate(zip(photos,products,strict=True)):
        path=root/f'scene-{i}.png'
        scene(photo,product,settings,path,logo)
        paths.append(path)
    duration=settings['duration']
    overlap=min(0.35,duration/len(paths)/4)
    scene_duration=(duration+overlap*(len(paths)-1))/len(paths)
    args=['ffmpeg','-hide_banner','-loglevel','error','-y','-threads','1','-filter_complex_threads','1']
    for path in paths:
        args += ['-loop','1','-framerate',str(FPS),'-t',str(scene_duration+0.1),'-i',str(path)]
    filters=[f'[{i}:v]format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS,fps={FPS}[v{i}]' for i in range(len(paths))]
    previous='v0'
    for i in range(1,len(paths)):
        output=f'x{i}'
        filters.append(f'[{previous}][v{i}]xfade=transition=fade:duration={overlap}:offset={i*(scene_duration-overlap)}[{output}]')
        previous=output
    output=root/'advertisement.mp4'
    args += ['-filter_complex',';'.join(filters),'-map',f'[{previous}]','-t',str(duration),'-r',str(FPS),'-c:v','libx264','-threads','1','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
    command(args)
    probe=json.loads(command(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)],30))
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    if video['width']!=WIDTH or video['height']!=HEIGHT or abs(float(probe['format']['duration'])-duration)>0.15:
        raise RuntimeError('Video output validation failed.')
    return output.read_bytes()
