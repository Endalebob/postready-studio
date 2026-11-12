"""1080px advertisement composition using canonical facts and bundled Ethiopic font."""
import base64
import io
from PIL import Image, ImageDraw, ImageOps
from .video_render import THEMES, font, width

def text(draw, value, baseline, max_lines, size, color):
    for chosen in range(size, 21, -2):
        lines = []; line = ''
        for word in value.split():
            next_line = (line + ' ' + word).strip()
            if width(next_line, chosen) > 940 and line:
                lines.append(line); line = word
            else:
                line = next_line
        if line:
            lines.append(line)
        if len(lines) <= max_lines and all(width(line, chosen) <= 940 for line in lines):
            for index, line in enumerate(lines):
                x = 70; y = baseline + index * (chosen + 9)
                for char in line:
                    face = font(chosen, char)
                    draw.text((x, y), char, font=face, fill=color, anchor='ls')
                    x += face.getlength(char)
            return
    raise ValueError('Shorten the advertisement text to fit the image.')

def decode(asset):
    data = base64.b64decode(asset['base64'], validate=True)
    if len(data) > 10 * 1024 * 1024:
        raise ValueError('Image is too large to render.')
    with Image.open(io.BytesIO(data)) as image:
        if image.width * image.height > 20_000_000:
            raise ValueError('Image dimensions are too large.')
        return image.convert('RGBA')

def render(result):
    details = result['details']
    background, ink, price, contact, accent = THEMES[details['theme']]
    canvas = Image.new('RGB', (1080, 1080), background); draw = ImageDraw.Draw(canvas)
    artwork = ImageOps.contain(decode(result['artwork']), (980, 575))
    canvas.paste(artwork, ((1080-artwork.width)//2, 30+(575-artwork.height)//2), artwork)
    if result.get('logo'):
        logo = ImageOps.contain(decode(result['logo']), (130, 90))
        draw.rectangle((870, 40, 1019, 149), fill='white')
        canvas.paste(logo, (880+(130-logo.width)//2, 50+(90-logo.height)//2), logo)
    draw.rectangle((40, 620, 1039, 623), fill=price)
    text(draw, result['image_text']['headline'], 684, 2, 46, price if details['theme']=='bold-contrast' else ink)
    text(draw, result['image_text']['tagline'], 804, 2, 28, ink)
    am = details['language'] == 'am'
    label = details['current_price'] + (' ብር' if am else ' ETB')
    if details.get('old_price'):
        label += f" · {'ቅናሽ' if am else 'Save'} {result['discount_percent']}% ({details['old_price']})"
    text(draw, label, 875, 1, 34, price)
    if details.get('address'):
        text(draw, details['address'], 923, 1, 24, ink)
    for index, item in enumerate(details['contacts']):
        text(draw, item['kind']+': '+item['value'], 960+index*25, 1, 22, contact)
    for x in range(40, 1040, 24):
        draw.rectangle((x, 1042, x+13, 1049), fill=accent if x%48==40 else price)
    output = io.BytesIO(); canvas.save(output, format='PNG')
    return output.getvalue()
