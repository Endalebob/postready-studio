import asyncio
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from pydantic import ValidationError
from .schemas import Details
from .images import normalize_image, MAX_BYTES
from .gemini import generate
from .accounts import router as accounts_router, current_user, Profile, User
from .logos import router as logos_router
from .database import database
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from . import storage
from .ads import router as ads_router, persist_generation
from .telegram import router as telegram_router
from .videos import router as videos_router
from .gallery import router as gallery_router
from .campaigns import router as campaigns_router
from .preparations import router as preparations_router
from .admin import router as admin_router
from .accounts import consume_image_request, worker_access
import base64


app = FastAPI(title='PostReady Studio')
app.include_router(accounts_router)
app.include_router(logos_router)
app.include_router(ads_router)
app.include_router(telegram_router)
app.include_router(videos_router)
app.include_router(gallery_router)
app.include_router(campaigns_router)
app.include_router(preparations_router)
app.include_router(admin_router)

@app.middleware('http')
async def mutation_guard(request: Request, call_next):
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        origin = request.headers.get('origin')
        allowed = os.getenv('APP_ORIGIN', 'http://localhost:3010').split(',')
        if request.headers.get('x-postready') != '1' or (origin and origin not in allowed):
            return JSONResponse({'detail': 'Request not allowed.'}, status_code=403)
    response = await call_next(request)
    if request.url.path != '/health':
        response.headers['Cache-Control'] = 'private, no-store'
    return response


@app.get('/health')
def health():
    return {'status': 'ok', 'generation_configured': bool(os.getenv('GEMINI_API_KEY'))}

@app.post('/generate')
async def create_ad(photo: UploadFile = File(...), details: str = Form(...), include_logo: bool = Form(True), user: User = Depends(current_user), db: Session = Depends(database)):
    owner = user.id
    try:
        values = Details.model_validate_json(details)
    except ValidationError as exc:
        raise HTTPException(422, [{'field': '.'.join(map(str,e['loc'])), 'message': e['msg']} for e in exc.errors()])
    try:
        image = normalize_image(await photo.read(MAX_BYTES+1))
    finally:
        await photo.close()
    logo = None
    profile = db.get(Profile, owner)
    if include_logo and profile and profile.logo_key:
        try:
            logo = {'mime_type': 'image/png', 'base64': base64.b64encode(await run_in_threadpool(storage.get, profile.logo_key)).decode()}
        except Exception:
            raise HTTPException(503, 'Could not load your logo. Please try again.')
    business_name = profile.data['business_name'] if profile else None
    consume_image_request(db, owner)
    db.commit()  # Reserve an attempt before a provider call; uncertain failures still consume it.
    db.close()  # Do not hold a database connection during a long provider call.
    def recheck_access():
        try:
            if not worker_access(db, owner):
                raise HTTPException(403, 'Your workspace access requires admin approval.')
        finally:
            db.close()
    try:
        result = await asyncio.wait_for(generate(image, values, before_artwork=recheck_access), timeout=180)
        await run_in_threadpool(recheck_access)
        if logo:
            result['logo'] = logo
        if business_name:
            result['business_name'] = business_name
        return await run_in_threadpool(persist_generation, db, owner, result, image)
    except HTTPException:
        raise
    except asyncio.TimeoutError:
        raise HTTPException(504, 'We couldn’t create your ad. Please try again.')
    except Exception:
        raise HTTPException(503, 'We couldn’t create your ad. Please try again.')
