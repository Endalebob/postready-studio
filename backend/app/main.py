import asyncio
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import ValidationError
from .schemas import Details
from .images import normalize_image, MAX_BYTES
from .gemini import generate

app = FastAPI(title='PostReady Studio')

@app.get('/health')
def health():
    return {'status': 'ok', 'generation_configured': bool(os.getenv('GEMINI_API_KEY'))}

@app.post('/generate')
async def create_ad(photo: UploadFile = File(...), details: str = Form(...)):
    try:
        values = Details.model_validate_json(details)
    except ValidationError as exc:
        raise HTTPException(422, [{'field': '.'.join(map(str,e['loc'])), 'message': e['msg']} for e in exc.errors()])
    try:
        image = normalize_image(await photo.read(MAX_BYTES+1))
    finally:
        await photo.close()
    try:
        return await asyncio.wait_for(generate(image, values), timeout=180)
    except asyncio.TimeoutError:
        raise HTTPException(504, 'We couldn’t create your ad. Please try again.')
    except Exception:
        raise HTTPException(503, 'We couldn’t create your ad. Please try again.')
