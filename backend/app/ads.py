import base64
import hashlib
import hmac
import io
import json
import os
import uuid
from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field, ValidationError
from PIL import Image, UnidentifiedImageError
from sqlalchemy import JSON, DateTime, ForeignKey, String, select, and_
from sqlalchemy.orm import Mapped, Session, mapped_column
from .database import Base, database
from .accounts import User, current_user, now, aware
from .schemas import Details
from . import storage

router = APIRouter()

class Ad(Base):
    __tablename__ = 'ads'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revision: Mapped[int]
    payload: Mapped[dict] = mapped_column(JSON)
    sources: Mapped[dict] = mapped_column(JSON)
    pending_sources: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    deleted: Mapped[bool] = mapped_column(default=False)

class AdRevision(Base):
    __tablename__ = 'ad_revisions'
    ad_id: Mapped[str] = mapped_column(ForeignKey('ads.id', ondelete='CASCADE'), primary_key=True)
    revision: Mapped[int] = mapped_column(primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    png_key: Mapped[str] = mapped_column(String(200))

class ImageText(BaseModel):
    headline: str = Field(min_length=1, max_length=100)
    tagline: str = Field(max_length=180)

class Edit(BaseModel):
    revision: int = Field(ge=1)
    details: Details
    image_text: ImageText
    social_caption: str = Field(max_length=1500)

def prefix(ad):
    return f'ads/{ad.owner_id}/{ad.id}/'

def receipt(owner, ad_id, expiry):
    message = f'{owner}|{ad_id}|{expiry}'
    signature = hmac.new(os.environ['MINIO_SECRET_KEY'].encode(), ('postready-generation:'+message).encode(), hashlib.sha256).hexdigest()
    return {'id': ad_id, 'expires_at': expiry, 'signature': signature}

def owned(db, owner, ad_id, lock=False):
    query = select(Ad).where(Ad.id == ad_id, Ad.owner_id == owner, Ad.deleted == False)
    if lock:
        query = query.with_for_update()
    ad = db.scalar(query)
    if not ad:
        raise HTTPException(404, 'Advertisement not found.')
    if aware(ad.expires_at) <= now():
        raise HTTPException(410, 'This advertisement has expired.')
    return ad

def copy_payload(result):
    return {k: result[k] for k in ('details', 'image_text', 'social_caption', 'discount_percent', 'business_name') if k in result}

def flush_sources(ad):
    if not ad.pending_sources:
        return
    refs = {}
    for kind, asset in ad.pending_sources.items():
        key = prefix(ad)+kind
        storage.put(key, base64.b64decode(asset['base64']), asset['mime_type'])
        refs[kind] = {'key': key, 'mime_type': asset['mime_type']}
    ad.sources = refs
    ad.pending_sources = None

def metadata(ad, has_png=False):
    return {'id': ad.id, 'revision': ad.revision, 'expires_at': aware(ad.expires_at).isoformat(),
            'created_at': aware(ad.created_at).isoformat(), 'storage_ready': ad.pending_sources is None,
            'has_png': has_png, 'renderer_version': 1}

def persist_generation(db, owner, result, photo):
    timestamp = now()
    ad_id = str(uuid.uuid4())
    expiry = timestamp+timedelta(days=7)
    signed = receipt(owner, ad_id, expiry.isoformat())
    assets = {'artwork': result['artwork'], 'source_photo': {'mime_type': 'image/jpeg', 'base64': base64.b64encode(photo).decode()}}
    if result.get('logo'):
        assets['logo'] = result['logo']
    ad = Ad(id=ad_id, owner_id=owner, created_at=timestamp, expires_at=expiry, revision=1,
            payload=copy_payload(result), sources={}, pending_sources=assets, deleted=False)
    try:
        db.add(ad)
        db.commit()
    except Exception:
        db.rollback()
        return {**result, 'receipt': signed, 'source_photo': assets['source_photo'], 'storage_ready': False,
                'expires_at': expiry.isoformat(), 'persistence_error': 'Your ad is not saved yet. Download it now or retry saving.'}
    try:
        flush_sources(ad)
        db.commit()
    except Exception:
        db.rollback()
        ad = db.get(Ad, ad_id)
    return {**result, **metadata(ad), 'receipt': signed}

def hydrated(ad):
    assets = {}
    try:
        for kind in ('artwork', 'logo'):
            if ad.pending_sources and kind in ad.pending_sources:
                assets[kind] = ad.pending_sources[kind]
            elif kind in ad.sources:
                ref = ad.sources[kind]
                assets[kind] = {'mime_type': ref['mime_type'], 'base64': base64.b64encode(storage.get(ref['key'])).decode()}
    except Exception:
        raise HTTPException(503, 'Could not load your advertisement. Please try again.')
    if aware(ad.expires_at) <= now():
        raise HTTPException(410, 'This advertisement has expired.')
    return {**ad.payload, **assets, **metadata(ad)}

@router.get('/ads')
def library(user: User = Depends(current_user), db: Session = Depends(database)):
    rows = db.execute(select(Ad.id, Ad.revision, Ad.created_at, Ad.expires_at, Ad.payload, Ad.sources, AdRevision.png_key)
        .outerjoin(AdRevision, and_(AdRevision.ad_id == Ad.id, AdRevision.revision == Ad.revision))
        .where(Ad.owner_id == user.id, Ad.deleted == False, Ad.expires_at > now()).order_by(Ad.created_at.desc())).all()
    return [{'id': row.id, 'revision': row.revision, 'created_at': aware(row.created_at).isoformat(),
             'expires_at': aware(row.expires_at).isoformat(), 'storage_ready': 'artwork' in row.sources,
             'has_png': row.png_key is not None, 'renderer_version': 1,
             'product_name': row.payload['details']['product_name'], 'headline': row.payload['image_text']['headline']} for row in rows]

@router.get('/ads/{ad_id}')
def detail(ad_id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    ad = owned(db, user.id, ad_id)
    result = hydrated(ad)
    result['has_png'] = db.get(AdRevision, (ad.id, ad.revision)) is not None
    return result

def png_bytes(data):
    if len(data) > 5*1024*1024:
        raise HTTPException(413, 'The saved advertisement must be smaller than 5 MB.')
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != 'PNG' or image.size != (1080, 1080):
                raise HTTPException(422, 'Save a 1080 × 1080 PNG advertisement.')
            image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(422, 'Could not read the saved advertisement.')
    return data

def parse_edit(values):
    try:
        return Edit.model_validate_json(values)
    except ValidationError:
        raise HTTPException(422, 'Check your advertisement details before saving.')

def save_revision(db, ad, values, png):
    if values.revision != ad.revision:
        raise HTTPException(409, 'This ad was updated elsewhere. Reopen it from My Ads before saving.')
    previous = ad.revision
    payload = {**ad.payload, 'details': values.details.model_dump(mode='json'), 'image_text': values.image_text.model_dump(),
               'social_caption': values.social_caption, 'discount_percent': values.details.discount}
    key = prefix(ad)+f'revisions/{previous+1}.png'
    try:
        flush_sources(ad)
        storage.put(key, png)
        # Expiry is checked again after storage I/O, before committing a new revision.
        if aware(ad.expires_at) <= now():
            db.rollback()
            raise HTTPException(410, 'This advertisement has expired.')
        ad.revision = previous+1
        ad.payload = payload
        db.add(AdRevision(ad_id=ad.id, revision=ad.revision, payload=payload, png_key=key))
        db.commit()
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(503, 'Could not save your ad. Your edits are still here. Please retry saving.')
    return metadata(ad, True)

@router.put('/ads/{ad_id}')
def save(ad_id: str, edits: str = Form(...), png: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(database)):
    ad = owned(db, user.id, ad_id, True)
    values = parse_edit(edits)
    try:
        data = png_bytes(png.file.read(5*1024*1024+1))
    finally:
        png.file.close()
    return save_revision(db, ad, values, data)

@router.post('/ads')
def recover(edits: str = Form(...), generated: UploadFile = File(...), png: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(database)):
    values = parse_edit(edits)
    try:
        encoded = generated.file.read(40*1024*1024+1)
        generated.file.close()
        if len(encoded) > 40*1024*1024:
            raise ValueError()
        result = json.loads(encoded)
        signed = result['receipt']
        expected = receipt(user.id, str(uuid.UUID(signed['id'])), signed['expires_at'])
        if not hmac.compare_digest(expected['signature'], signed['signature']):
            raise ValueError()
        expiry = datetime.fromisoformat(signed['expires_at'])
        if aware(expiry) <= now():
            raise HTTPException(410, 'This advertisement has expired.')
        assets = {k: result[k] for k in ('artwork', 'source_photo', 'logo') if k in result}
        if not all(k in assets for k in ('artwork', 'source_photo')):
            raise ValueError()
        for asset in assets.values():
            data = base64.b64decode(asset['base64'], validate=True)
            if len(data) > 10*1024*1024 or asset['mime_type'] not in ('image/png', 'image/jpeg', 'image/webp'):
                raise ValueError()
            with Image.open(io.BytesIO(data)) as image:
                if image.width*image.height > 20_000_000:
                    raise ValueError()
                image.verify()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, 'Could not restore this generated advertisement.')
    ad = db.get(Ad, signed['id'])
    if ad is None:
        ad = Ad(id=signed['id'], owner_id=user.id, created_at=expiry-timedelta(days=7), expires_at=expiry,
                revision=1, payload=copy_payload(result), sources={}, pending_sources=assets, deleted=False)
        db.add(ad)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(503, 'Could not save your ad. Please retry saving.')
    ad = owned(db, user.id, signed['id'], True)
    try:
        data = png_bytes(png.file.read(5*1024*1024+1))
    finally:
        png.file.close()
    return save_revision(db, ad, values, data)

@router.get('/ads/{ad_id}/thumbnail')
def thumbnail(ad_id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    ad = owned(db, user.id, ad_id)
    revision = db.get(AdRevision, (ad.id, ad.revision))
    try:
        if revision:
            data = storage.get(revision.png_key)
        elif ad.pending_sources and 'artwork' in ad.pending_sources:
            data = base64.b64decode(ad.pending_sources['artwork']['base64'])
        else:
            data = storage.get(ad.sources['artwork']['key'])
        with Image.open(io.BytesIO(data)) as image:
            image.thumbnail((240, 240))
            output = io.BytesIO()
            image.convert('RGB').save(output, format='JPEG', quality=80)
    except Exception:
        raise HTTPException(503, 'Could not load the advertisement preview.')
    if aware(ad.expires_at) <= now():
        raise HTTPException(410, 'This advertisement has expired.')
    return Response(output.getvalue(), media_type='image/jpeg')

@router.get('/ads/{ad_id}/png')
def download(ad_id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    ad = owned(db, user.id, ad_id)
    revision = db.get(AdRevision, (ad.id, ad.revision))
    if not revision:
        raise HTTPException(409, 'Open this advertisement and save it before downloading the saved PNG.')
    try:
        data = storage.get(revision.png_key)
    except Exception:
        raise HTTPException(503, 'Could not download your ad. Please try again.')
    if aware(ad.expires_at) <= now():
        raise HTTPException(410, 'This advertisement has expired.')
    return Response(data, media_type='image/png', headers={'Content-Disposition': 'attachment; filename="postready-ad.png"'})

@router.delete('/ads/{ad_id}')
def delete_ad(ad_id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    ad = owned(db, user.id, ad_id, True)
    ad.deleted = True
    db.commit()
    return {'ok': True}

def cleanup(db):
    # The row remains until every object deletion succeeds; retries are idempotent.
    ads = db.scalars(select(Ad).where((Ad.expires_at <= now()) | (Ad.deleted == True)).with_for_update(skip_locked=True).limit(100)).all()
    removed = 0
    for ad in ads:
        try:
            storage.remove_prefix(prefix(ad))
            db.delete(ad)
            db.commit()
            removed += 1
        except Exception:
            db.rollback()
    return removed
