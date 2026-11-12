"""Explicit, durable campaign preparation. Provider phases are never blindly replayed."""
import asyncio
import base64
import os
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, select, func
from sqlalchemy.orm import Mapped, Session, mapped_column
from .accounts import User, Profile, current_user, now, aware
from .database import Base, database
from .campaigns import Campaign, owned as campaign_owned, eligible
from .gallery import GalleryAsset
from .telegram import Connection
from .schemas import Details, Copy
from .ads import Ad, AdRevision, copy_payload, flush_sources, prefix
from . import ad_render, gemini, storage

from .accounts import admin_user, worker_access, consume_image_request
router = APIRouter(dependencies=[Depends(admin_user)])
ACTIVE = ('queued', 'copying', 'copy_ready', 'artwork_calling', 'artwork_ready')
TERMINAL = ('ready', 'needs_edit', 'failed', 'unknown')

class Preparation(Base):
    __tablename__ = 'campaign_preparations'
    __table_args__ = (UniqueConstraint('owner_id', 'request_key', name='uq_preparation_owner_request'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey('campaigns.id', ondelete='CASCADE'), index=True)
    request_key: Mapped[str] = mapped_column(String(36))
    ad_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(30), index=True)
    snapshot: Mapped[dict] = mapped_column(JSON)
    assets: Mapped[dict] = mapped_column(JSON)
    output: Mapped[dict] = mapped_column(JSON)
    detail: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Start(BaseModel):
    model_config = {'extra': 'forbid'}
    request_key: uuid.UUID
    campaign_revision: int = Field(ge=1, strict=True)
    gallery_id: uuid.UUID
    gallery_revision: int = Field(ge=1, strict=True)
    confirmed: bool

def view(db, row):
    ad = db.get(Ad, row.ad_id) if row.status in ('ready', 'needs_edit') else None
    valid = bool(ad and not ad.deleted and aware(ad.expires_at) > now())
    return {'id': row.id, 'campaign_id': row.campaign_id, 'status': row.status, 'detail': row.detail,
            'product_name': row.snapshot['details']['product_name'], 'ad_id': row.ad_id if valid else None,
            'ad_available': valid, 'created_at': aware(row.created_at).isoformat(),
            'updated_at': aware(row.updated_at).isoformat()}

def owned(db, owner, id, lock=False):
    query = select(Preparation).where(Preparation.id == id, Preparation.owner_id == owner)
    row = db.scalar(query.with_for_update() if lock else query)
    if not row:
        raise HTTPException(404, 'Preparation not found.')
    return row

def valid_inputs(db, row):
    campaign = db.scalar(select(Campaign).where(Campaign.id == row.campaign_id).with_for_update().execution_options(populate_existing=True))
    connection = db.scalar(select(Connection).where(Connection.owner_id == row.owner_id).with_for_update().execution_options(populate_existing=True))
    gallery = db.scalar(select(GalleryAsset).where(GalleryAsset.id == row.snapshot['gallery_id']).with_for_update().execution_options(populate_existing=True))
    return bool(worker_access(db, row.owner_id, admin_only=True) and campaign and not campaign.deleted and campaign.owner_id == row.owner_id
                and campaign.revision == row.snapshot['campaign_revision']
                and gallery and gallery.owner_id == row.owner_id and eligible(gallery)
                and gallery.revision == row.snapshot['gallery_revision']
                and gallery.id in campaign.settings['gallery_ids']
                and connection and connection.active and connection.connection_id == row.snapshot['connection_id'])

@router.post('/campaigns/{campaign_id}/preparations')
def start(campaign_id: str, values: Start, user: User = Depends(current_user), db: Session = Depends(database)):
    campaign = campaign_owned(db, user.id, campaign_id)
    if not values.confirmed:
        raise HTTPException(422, 'Confirm this generation request before continuing.')
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    existing = db.scalar(select(Preparation).where(Preparation.owner_id == user.id, Preparation.request_key == str(values.request_key)))
    if existing:
        if existing.campaign_id != campaign.id:
            raise HTTPException(409, 'Use a new request reference for another campaign.')
        return view(db, existing)
    if not os.getenv('GEMINI_API_KEY'):
        raise HTTPException(503, 'Image generation is not configured yet.')
    campaign = db.scalar(select(Campaign).where(Campaign.id == campaign.id).with_for_update().execution_options(populate_existing=True))
    connection = db.scalar(select(Connection).where(Connection.owner_id == user.id).with_for_update())
    gallery = db.scalar(select(GalleryAsset).where(GalleryAsset.id == str(values.gallery_id), GalleryAsset.owner_id == user.id).with_for_update())
    if campaign.deleted or campaign.revision != values.campaign_revision:
        raise HTTPException(409, 'This campaign changed. Reopen it before preparing an advertisement.')
    if not eligible(gallery) or gallery.revision != values.gallery_revision or gallery.id not in campaign.settings['gallery_ids']:
        raise HTTPException(409, 'Choose a currently approved product from this campaign. Refresh and review it again.')
    if not connection or not connection.active or connection.connection_id != campaign.settings['connection_id']:
        raise HTTPException(409, 'Reconnect and save the campaign destination before preparing an ad.')
    if db.scalar(select(func.count()).select_from(Preparation).where(Preparation.owner_id == user.id, Preparation.status.in_(ACTIVE))) >= 2:
        raise HTTPException(409, 'Finish or resolve your existing preparations before starting another. Up to two may be in progress.')
    if db.scalar(select(func.count()).select_from(Preparation).where(Preparation.owner_id == user.id, Preparation.created_at > now()-timedelta(days=1))) >= 10:
        raise HTTPException(429, 'You can request up to ten campaign preparations in 24 hours. Try again later.')
    profile = db.get(Profile, user.id)
    try:
        assets = {'source_photo': {'mime_type': 'image/jpeg', 'base64': base64.b64encode(storage.get(gallery.storage_key)).decode()}}
        if profile and profile.logo_key:
            assets['logo'] = {'mime_type': 'image/png', 'base64': base64.b64encode(storage.get(profile.logo_key)).decode()}
    except Exception:
        raise HTTPException(503, 'Could not load your product photo or logo. Please try again.')
    details = Details.model_validate({**gallery.details, 'language': campaign.settings['language'], 'theme': campaign.settings['theme']})
    snapshot = {'details': details.model_dump(mode='json'), 'gallery_id': gallery.id, 'gallery_revision': gallery.revision,
                'campaign_revision': campaign.revision, 'connection_id': connection.connection_id,
                'instructions': campaign.settings['instructions'], 'notes': gallery.campaign_notes,
                'business_name': profile.data.get('business_name', '') if profile else ''}
    consume_image_request(db, user.id)
    row = Preparation(id=str(uuid.uuid4()), owner_id=user.id, campaign_id=campaign.id, request_key=str(values.request_key),
                      ad_id=str(uuid.uuid4()), status='queued', snapshot=snapshot, assets=assets, output={},
                      detail=None, created_at=now(), updated_at=now())
    db.add(row); db.commit()
    return view(db, row)

@router.get('/campaigns/{campaign_id}/preparations')
def library(campaign_id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    campaign_owned(db, user.id, campaign_id)
    return [view(db, row) for row in db.scalars(select(Preparation).where(Preparation.campaign_id == campaign_id, Preparation.owner_id == user.id).order_by(Preparation.created_at.desc()).limit(20))]

@router.get('/preparations/{id}')
def get_item(id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    return view(db, owned(db, user.id, id))

@router.post('/preparations/{id}/retry-finalization')
def retry_finalization(id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    row = owned(db, user.id, id, True)
    if row.status != 'retryable':
        raise HTTPException(409, 'Only saving and rendering can be retried. Uncertain provider requests are never automatically repeated.')
    if not valid_inputs(db, row):
        raise HTTPException(409, 'The campaign or approved product changed. Review them before preparing another ad.')
    row.status = 'artwork_ready'; row.detail = None; row.updated_at = now(); db.commit()
    return view(db, row)

def finish(row, status, detail=None):
    row.status = status; row.detail = detail; row.updated_at = now()

def finalize(db, row):
    details = Details.model_validate(row.snapshot['details'])
    result = {'details': details.model_dump(mode='json'), 'image_text': {key: row.output['copy'][key] for key in ('headline', 'tagline')},
              'social_caption': row.output['copy']['social_caption'], 'discount_percent': details.discount,
              'business_name': row.snapshot['business_name'], 'artwork': row.output['artwork']}
    if row.assets.get('logo'):
        result['logo'] = row.assets['logo']
    generated = datetime.fromisoformat(row.output['generated_at'])
    if aware(generated)+timedelta(days=30) <= now():
        finish(row, 'failed', 'This prepared artwork has expired. Request a new preparation.'); db.commit(); return
    ad = Ad(id=row.ad_id, owner_id=row.owner_id, created_at=generated, expires_at=generated+timedelta(days=30),
            revision=1, payload=copy_payload(result), sources={}, pending_sources={**row.assets, 'artwork': result['artwork']}, deleted=False)
    db.add(ad); db.flush(); flush_sources(ad)
    try:
        png = ad_render.render(result)
    except ValueError:
        finish(row, 'needs_edit', 'Artwork is saved. Open the ad and shorten its text before saving the PNG.')
    else:
        key = prefix(ad)+'revisions/1.png'; storage.put(key, png, 'image/png')
        db.add(AdRevision(ad_id=ad.id, revision=1, payload=ad.payload, png_key=key))
        finish(row, 'ready')
    row.assets = {}; row.output = {}; db.commit()

def process(db):
    stale = db.scalars(select(Preparation).where(Preparation.status.in_(('copying', 'artwork_calling')), Preparation.updated_at < now()-timedelta(minutes=10)).with_for_update(skip_locked=True)).all()
    for row in stale:
        finish(row, 'unknown', 'Generation stopped without a confirmed result. It will not be resubmitted automatically; the provider may have charged for the request.')
    db.commit()
    row = db.scalar(select(Preparation).where(Preparation.status.in_(('queued', 'copy_ready', 'artwork_ready'))).order_by(Preparation.created_at).with_for_update(skip_locked=True).limit(1))
    if not row:
        return 0
    if not valid_inputs(db, row) or not os.getenv('GEMINI_API_KEY'):
        finish(row, 'failed', 'The campaign, channel or approved product changed. Review it before preparing another ad.'); db.commit(); return 1
    if row.status == 'artwork_ready':
        id = row.id
        try:
            finalize(db, row)
        except Exception:
            db.rollback(); row = db.get(Preparation, id)
            finish(row, 'retryable', 'Artwork is ready but could not be saved. Retry saving without another AI request.'); db.commit()
        return 1
    id = row.id; phase = 'copying' if row.status == 'queued' else 'artwork_calling'
    snapshot = row.snapshot; assets = row.assets
    finish(row, phase); db.commit()  # Commit before any provider call; never replay an in-flight phase.
    db.close()
    try:
        details = Details.model_validate(snapshot['details'])
        if phase == 'copying':
            output = Copy.model_validate(asyncio.run(gemini.campaign_copy(details, snapshot['instructions'], snapshot['notes']))).model_dump()
        else:
            output = asyncio.run(gemini.campaign_artwork(base64.b64decode(assets['source_photo']['base64']), details.theme))
        error = None
    except Exception as exc:
        code = getattr(exc, 'code', None)
        error = 'failed' if isinstance(exc, (ValueError, HTTPException)) or (isinstance(code, int) and 400 <= code < 500) else 'unknown'
    db.expire_all()
    row = db.scalar(select(Preparation).where(Preparation.id == id).with_for_update().execution_options(populate_existing=True))
    if not row or row.status != phase:
        db.rollback(); return 1
    if error:
        finish(row, error, 'The provider did not return usable content. Review the product and try a new preparation.' if error=='failed' else 'The provider result is uncertain. It may have charged for the request. This preparation will not be resubmitted automatically.')
    else:
        row.output = {**row.output, ('copy' if phase=='copying' else 'artwork'): output,
                      **({'generated_at': now().isoformat()} if phase=='artwork_calling' else {})}
        finish(row, 'copy_ready' if phase=='copying' else 'artwork_ready')
    db.commit(); return 1

def cleanup(db):
    rows = db.scalars(select(Preparation).where(Preparation.created_at < now()-timedelta(days=30), Preparation.status.notin_(('copying', 'artwork_calling'))).with_for_update(skip_locked=True).limit(100)).all()
    for row in rows:
        if not db.get(Ad, row.ad_id):
            storage.remove_prefix(f'ads/{row.owner_id}/{row.ad_id}/')
        db.delete(row)
    db.commit(); return len(rows)
