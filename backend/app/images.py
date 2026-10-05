import io
import warnings
from PIL import Image, ImageOps
from fastapi import HTTPException

MAX_BYTES = 10 * 1024 * 1024

def normalize_image(data: bytes) -> bytes:
    if len(data) > MAX_BYTES:
        raise HTTPException(413, 'Choose an image smaller than 10 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ('JPEG', 'PNG', 'WEBP'):
                    raise HTTPException(415, 'Choose a JPEG, PNG, or WebP image.')
                if image.width * image.height > 20_000_000:
                    raise HTTPException(413, 'Choose an image below 20 megapixels.')
                image = ImageOps.exif_transpose(image).convert('RGB')
                image.thumbnail((2048, 2048))
                out = io.BytesIO()
                image.save(out, format='JPEG', quality=92)
                return out.getvalue()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(415, 'We cannot use this photo. Choose another JPEG, PNG, or WebP image.')
