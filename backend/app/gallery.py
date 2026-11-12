"""Private reusable product inputs, independent of generated-ad expiration."""
import io
import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, select, func
from sqlalchemy.orm import Mapped, Session, mapped_column
from PIL import Image
from .accounts import User, current_user, now, aware
from .database import Base, database
from .schemas import Details
from .images import normalize_image, MAX_BYTES
from . import storage

from .accounts import admin_user
router=APIRouter(dependencies=[Depends(admin_user)])
MAX_ITEMS=100

class GalleryAsset(Base):
    __tablename__='gallery_assets'
    __table_args__=(UniqueConstraint('owner_id','request_key',name='uq_gallery_owner_request'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    owner_id: Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    request_key: Mapped[str]=mapped_column(String(36))
    storage_key: Mapped[str]=mapped_column(String(200))
    details: Mapped[dict]=mapped_column(JSON)
    campaign_notes: Mapped[str]=mapped_column(String(600))
    revision: Mapped[int]
    active: Mapped[bool]=mapped_column(default=True)
    ready: Mapped[bool]=mapped_column(default=False)
    deleted: Mapped[bool]=mapped_column(default=False,index=True)
    approved_at: Mapped[object|None]=mapped_column(DateTime(timezone=True),nullable=True)
    created_at: Mapped[object]=mapped_column(DateTime(timezone=True))
    updated_at: Mapped[object]=mapped_column(DateTime(timezone=True))

class Facts(BaseModel):
    model_config={'extra':'forbid'}
    details: Details
    campaign_notes: str=Field(default='',max_length=600)

class Change(Facts):
    revision: int=Field(ge=1)
    active: bool=True

class Revision(BaseModel):
    model_config={'extra':'forbid'}
    revision: int=Field(ge=1)

def owned(db,owner,id,lock=False):
    query=select(GalleryAsset).where(GalleryAsset.id==id,GalleryAsset.owner_id==owner,GalleryAsset.deleted==False)
    row=db.scalar(query.with_for_update() if lock else query)
    if not row:
        raise HTTPException(404,'Gallery item not found.')
    if not row.ready:
        raise HTTPException(409,'This image upload is not complete. Refresh the gallery.')
    return row

def view(row):
    return {'id':row.id,'details':row.details,'campaign_notes':row.campaign_notes,'revision':row.revision,
            'active':row.active,'approved_at':aware(row.approved_at).isoformat() if row.approved_at else None,
            'eligible':bool(row.active and row.approved_at and row.ready and not row.deleted),
            'image_url':f'/api/backend/gallery/{row.id}/image','created_at':aware(row.created_at).isoformat(),
            'updated_at':aware(row.updated_at).isoformat()}

def check_revision(row,revision):
    if row.revision!=revision:
        raise HTTPException(409,'This gallery item changed in another tab. Refresh and review it again.')

@router.get('/gallery')
def library(user:User=Depends(current_user),db:Session=Depends(database)):
    return [view(row) for row in db.scalars(select(GalleryAsset).where(GalleryAsset.owner_id==user.id,GalleryAsset.deleted==False,GalleryAsset.ready==True).order_by(GalleryAsset.created_at.desc()).limit(MAX_ITEMS))]

@router.post('/gallery')
def create(facts:str=Form(...),request_key:str=Form(...),photo:UploadFile=File(...),user:User=Depends(current_user),db:Session=Depends(database)):
    try:
        try:
            values=Facts.model_validate_json(facts);request_key=str(uuid.UUID(request_key))
        except (ValidationError,ValueError):
            raise HTTPException(422,'Enter valid product facts, contacts and prices, and a valid upload reference.')
        existing=db.scalar(select(GalleryAsset).where(GalleryAsset.owner_id==user.id,GalleryAsset.request_key==request_key))
        if existing:
            return view(owned(db,user.id,existing.id))
        image=normalize_image(photo.file.read(MAX_BYTES+1))
    finally:
        photo.file.close()
    # Serialize admission and duplicate detection for this owner, including pending cleanup.
    db.scalar(select(User).where(User.id==user.id).with_for_update())
    existing=db.scalar(select(GalleryAsset).where(GalleryAsset.owner_id==user.id,GalleryAsset.request_key==request_key))
    if existing:
        return view(owned(db,user.id,existing.id))
    if db.scalar(select(func.count()).select_from(GalleryAsset).where(GalleryAsset.owner_id==user.id))>=MAX_ITEMS:
        raise HTTPException(409,'Your gallery holds up to 100 items. Remove an item and allow cleanup before adding another.')
    id=str(uuid.uuid4());row=GalleryAsset(id=id,owner_id=user.id,request_key=request_key,
        storage_key=f'gallery/{user.id}/{id}/source.jpg',details=values.details.model_dump(mode='json'),
        campaign_notes=values.campaign_notes,revision=1,active=True,ready=False,deleted=False,
        approved_at=None,created_at=now(),updated_at=now())
    db.add(row);db.commit()
    try:
        storage.put(row.storage_key,image,'image/jpeg');row.ready=True;row.updated_at=now();db.commit()
    except Exception:
        db.rollback();row=db.get(GalleryAsset,id);row.deleted=True;row.updated_at=now();db.commit()
        raise HTTPException(503,'Could not save this gallery image. Your form is still here; please try again.')
    return view(row)

@router.get('/gallery/{id}')
def get_item(id:str,user:User=Depends(current_user),db:Session=Depends(database)):
    return view(owned(db,user.id,id))

@router.put('/gallery/{id}')
def edit(id:str,values:Change,user:User=Depends(current_user),db:Session=Depends(database)):
    row=owned(db,user.id,id,True);check_revision(row,values.revision)
    details=values.details.model_dump(mode='json')
    if details!=row.details or values.campaign_notes!=row.campaign_notes or values.active!=row.active:
        row.approved_at=None
    row.details=details;row.campaign_notes=values.campaign_notes;row.active=values.active
    row.revision+=1;row.updated_at=now();db.commit();return view(row)

@router.post('/gallery/{id}/approve')
def approve(id:str,values:Revision,user:User=Depends(current_user),db:Session=Depends(database)):
    row=owned(db,user.id,id,True);check_revision(row,values.revision)
    if not row.active:
        raise HTTPException(409,'Activate and review this item before approving it.')
    row.approved_at=now();row.revision+=1;row.updated_at=now();db.commit();return view(row)

@router.post('/gallery/{id}/deactivate')
def deactivate(id:str,values:Revision,user:User=Depends(current_user),db:Session=Depends(database)):
    row=owned(db,user.id,id,True);check_revision(row,values.revision)
    row.active=False;row.approved_at=None;row.revision+=1;row.updated_at=now();db.commit();return view(row)

@router.delete('/gallery/{id}')
def delete_item(id:str,values:Revision,user:User=Depends(current_user),db:Session=Depends(database)):
    row=owned(db,user.id,id,True);check_revision(row,values.revision)
    row.deleted=True;row.active=False;row.approved_at=None;row.updated_at=now();db.commit()
    return {'ok':True}

@router.get('/gallery/{id}/image')
def image(id:str,thumbnail:bool=False,user:User=Depends(current_user),db:Session=Depends(database)):
    row=owned(db,user.id,id)
    try:
        data=storage.get(row.storage_key)
        if thumbnail:
            with Image.open(io.BytesIO(data)) as photo:
                photo.thumbnail((360,360));output=io.BytesIO();photo.save(output,format='JPEG',quality=82);data=output.getvalue()
    except Exception:
        raise HTTPException(503,'Could not load this gallery image. Please try again.')
    # Recheck a concurrent delete before returning private media.
    owned(db,user.id,id)
    return Response(data,media_type='image/jpeg',headers={'Cache-Control':'private, no-store'})

def cleanup(db):
    rows=db.scalars(select(GalleryAsset).where((GalleryAsset.deleted==True)|((GalleryAsset.ready==False)&(GalleryAsset.updated_at<now()-timedelta(minutes=10)))).with_for_update(skip_locked=True).limit(100)).all()
    count=0
    for row in rows:
        try:
            storage.remove_prefix(f'gallery/{row.owner_id}/{row.id}/');db.delete(row);db.commit();count+=1
        except Exception:
            db.rollback()
    return count
