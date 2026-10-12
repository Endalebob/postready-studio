import io
import re
import tempfile
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column
from PIL import Image
from .accounts import User, Profile, current_user, now, aware
from .database import Base, database
from .images import normalize_image, MAX_BYTES
from . import storage, video_render, video_audio, video_providers

router=APIRouter()

class Video(Base):
    __tablename__='videos'
    __table_args__=(UniqueConstraint('owner_id','request_key',name='uq_video_owner_request'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    owner_id: Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    request_key: Mapped[str]=mapped_column(String(36))
    status: Mapped[str]=mapped_column(String(20),index=True)
    details: Mapped[dict]=mapped_column(JSON)
    assets: Mapped[dict]=mapped_column(JSON)
    output_key: Mapped[str | None]=mapped_column(String(200),nullable=True)
    error: Mapped[str | None]=mapped_column(String(255),nullable=True)
    created_at: Mapped[object]=mapped_column(DateTime(timezone=True))
    updated_at: Mapped[object]=mapped_column(DateTime(timezone=True))
    expires_at: Mapped[object | None]=mapped_column(DateTime(timezone=True),nullable=True,index=True)

class Product(BaseModel):
    name: str=Field(min_length=1,max_length=100)
    price: str=Field(default='',max_length=20)
    description: str=Field(default='',max_length=180)

    @field_validator('name')
    @classmethod
    def clean_name(cls,value):
        value=value.strip()
        if not value:
            raise ValueError('Enter a product name for each photo.')
        return value

    @field_validator('price')
    @classmethod
    def valid_price(cls,value):
        value=value.strip()
        if not value:
            return ''
        try:
            price=Decimal(value)
            if not re.fullmatch(r'\d+(?:\.\d{1,2})?',value) or not price.is_finite() or price<=0 or price>999999999:
                raise ValueError()
        except (InvalidOperation,ValueError):
            raise ValueError('Enter a positive price with up to two decimal places.')
        return value

class Options(BaseModel):
    model_config={'extra':'forbid'}
    request_key: str=Field(min_length=36,max_length=36)
    mode: Literal['transitions','motion']='transitions'
    products: list[Product]=Field(min_length=1,max_length=10)
    duration: int=Field(ge=4,le=20)
    theme: Literal['ethiopian-warmth','bold-contrast','clean-modern']
    language: Literal['en','am']
    include_logo: bool=True
    music: Literal['none','upload','elegant-piano','bright-strings','warm-acoustic','grand-showcase','calm-classical']='none'
    provider: Literal['bfl','google']='bfl'
    cost_acknowledged: bool=False

    @model_validator(mode='after')
    def valid_video(self):
        if self.mode=='transitions' and self.duration not in (5,10,15):
            raise ValueError('Choose 5, 10 or 15 seconds for photo transitions.')
        if self.mode=='motion':
            supported=range(5,21) if self.provider=='bfl' else (4,6,8)
            if self.duration not in supported:
                raise ValueError('Choose a supported duration for this provider.')
            if not self.cost_acknowledged:
                raise ValueError('Review and accept the estimated provider cost before generating.')
        return self

    @field_validator('request_key')
    @classmethod
    def valid_key(cls,value):
        return str(uuid.UUID(value))

def prefix(row):
    return f'videos/{row.owner_id}/{row.id}/'

def view(row):
    return {'id':row.id,'status':row.status,'title':row.details['products'][0]['name'],
            'duration':row.details['duration'],'photo_count':len(row.details['products']),
            'mode':row.details.get('mode','transitions'),'provider':row.details.get('provider') if row.details.get('mode')=='motion' else None,
            'estimated_cost':row.details.get('estimated_cost'),
            'created_at':aware(row.created_at).isoformat(),
            'expires_at':aware(row.expires_at).isoformat() if row.expires_at else None,'error':row.error,
            'media_url':f'/api/backend/videos/{row.id}/media' if row.status=='ready' else None}

def owned(db,owner,id):
    row=db.scalar(select(Video).where(Video.id==id,Video.owner_id==owner))
    if not row:
        raise HTTPException(404,'Video not found.')
    if row.expires_at and aware(row.expires_at)<=now():
        raise HTTPException(410,'This video has expired.')
    return row

@router.get('/videos')
def library(user:User=Depends(current_user),db:Session=Depends(database)):
    rows=db.scalars(select(Video).where(Video.owner_id==user.id).order_by(Video.created_at.desc()).limit(50)).all()
    return [view(row) for row in rows if not row.expires_at or aware(row.expires_at)>now()]

@router.get('/videos/music/{preset}')
def music_preview(preset:str,user:User=Depends(current_user)):
    if preset not in video_audio.PRESETS:
        raise HTTPException(404,'Music preset not found.')
    return Response((video_audio.MUSIC_ROOT/(preset+'.wav')).read_bytes(),media_type='audio/wav')

@router.get('/videos/providers/options')
def provider_options(user:User=Depends(current_user)):
    return video_providers.options()

@router.get('/videos/{video_id}')
def status(video_id:str,user:User=Depends(current_user),db:Session=Depends(database)):
    return view(owned(db,user.id,video_id))

@router.post('/videos')
def create(options:str=Form(...),photos:list[UploadFile]=File(...),music:UploadFile|None=File(None),voice:UploadFile|None=File(None),user:User=Depends(current_user),db:Session=Depends(database)):
    try:
        values=Options.model_validate_json(options)
        if len(photos)!=len(values.products):
            raise HTTPException(422,'Add one product description for each photo, up to ten photos.')
        # Duplicate submissions are returned without storing another set of assets.
        existing=db.scalar(select(Video).where(Video.owner_id==user.id,Video.request_key==values.request_key))
        if existing:
            return view(existing)
        if values.mode=='motion':
            try:
                video_providers.key(values.provider)
            except video_providers.ProviderFailure as exc:
                raise HTTPException(503,str(exc))
        if (values.music=='upload') != bool(music):
            raise HTTPException(422,'Upload a music file when choosing your own music.')
        audio={}
        if music:
            audio['music']=video_audio.normalize(music.file.read(video_audio.MAX_AUDIO_BYTES+1),'Music',60)
        if voice:
            audio['voice']=video_audio.normalize(voice.file.read(video_audio.MAX_AUDIO_BYTES+1),'Voice',values.duration)
        images=[normalize_image(photo.file.read(MAX_BYTES+1)) for photo in photos]
        # Normalize again to the export's useful resolution, limiting working memory.
        normalized=[]
        for data in images:
            with Image.open(io.BytesIO(data)) as image:
                image.thumbnail((1280,1280)); output=io.BytesIO(); image.save(output,format='JPEG',quality=90); normalized.append(output.getvalue())
    except ValidationError as exc:
        raise HTTPException(422,[{'msg':e['msg']} for e in exc.errors()])
    finally:
        for upload in [*photos,music,voice]:
            if upload:
                upload.file.close()
    # Serialize admission per account so parallel requests cannot exceed its limit.
    db.scalar(select(User).where(User.id==user.id).with_for_update())
    existing=db.scalar(select(Video).where(Video.owner_id==user.id,Video.request_key==values.request_key))
    if existing:
        return view(existing)
    active=db.scalars(select(Video.id).where(Video.owner_id==user.id,Video.status.in_(['staging','queued','processing','generating','submitting']))).all()
    if len(active)>=2:
        raise HTTPException(429,'Wait for your current videos to finish before creating another.')
    profile=db.get(Profile,user.id)
    details=values.model_dump(mode='json')
    if values.mode=='motion':
        details['estimated_cost']=video_providers.estimate(values.provider,values.duration,len(values.products))
    details.update({'business_name':profile.data['business_name'] if profile else '',
                    'contacts':profile.data['contacts'] if profile else [],'address':profile.data['address'] if profile else ''})
    row=Video(id=str(uuid.uuid4()),owner_id=user.id,request_key=values.request_key,status='staging',details=details,
              assets={},output_key=None,error=None,created_at=now(),updated_at=now(),expires_at=None)
    db.add(row);db.commit()
    try:
        refs=[]
        for i,image in enumerate(normalized):
            key=prefix(row)+f'photos/{i}.jpg';storage.put(key,image,'image/jpeg');refs.append(key)
        assets={'photos':refs}
        for kind,data in audio.items():
            key=prefix(row)+kind+'.wav';storage.put(key,data,'audio/wav');assets[kind]=key
        if values.include_logo and profile and profile.logo_key:
            key=prefix(row)+'logo.png';storage.put(key,storage.get(profile.logo_key));assets['logo']=key
        row.assets=assets;row.status='queued';row.updated_at=now();db.commit()
    except Exception:
        db.rollback();row=db.get(Video,row.id);row.status='failed';row.error='Could not store your photos. Your form is still available; please try again.';row.updated_at=now();db.commit()
    return view(row)

@router.get('/videos/{video_id}/media')
def media(video_id:str,request:Request,download:bool=False,user:User=Depends(current_user),db:Session=Depends(database)):
    row=owned(db,user.id,video_id)
    if row.status!='ready' or not row.output_key:
        raise HTTPException(409,'The video is not ready yet.')
    try:
        data=storage.get(row.output_key)
    except Exception:
        raise HTTPException(503,'Could not load your video. Please try again.')
    if aware(row.expires_at)<=now():
        raise HTTPException(410,'This video has expired.')
    headers={'Accept-Ranges':'bytes','Content-Disposition':('attachment' if download else 'inline')+'; filename="postready-video.mp4"'}
    range_header=request.headers.get('range')
    if range_header:
        match=re.fullmatch(r'bytes=(\d*)-(\d*)',range_header) if len(range_header)<100 else None
        if not match or not any(match.groups()):
            return Response(status_code=416,headers={'Content-Range':f'bytes */{len(data)}'})
        a,b=match.groups()
        start=int(a) if a else max(0,len(data)-int(b))
        end=min(int(b),len(data)-1) if a and b else len(data)-1
        if start>=len(data) or end<start:
            return Response(status_code=416,headers={'Content-Range':f'bytes */{len(data)}'})
        headers['Content-Range']=f'bytes {start}-{end}/{len(data)}'
        return Response(data[start:end+1],status_code=206,media_type='video/mp4',headers=headers)
    return Response(data,media_type='video/mp4',headers=headers)

def process_video(db):
    from .video_motion import advance
    motion_id=advance(db)
    # Local rendering is safely repeatable. Recover jobs after a stopped worker.
    old=now()-timedelta(minutes=10)
    for row in db.scalars(select(Video).where(Video.status=='processing',Video.updated_at<old).with_for_update(skip_locked=True)).all():
        if row.details.get('mode','transitions')=='transitions':
            row.status='queued';row.updated_at=now()
    for row in db.scalars(select(Video).where(Video.status=='staging',Video.updated_at<old).with_for_update(skip_locked=True)).all():
        row.status='failed';row.error='Photo upload was interrupted. Please submit your video again.';row.updated_at=now()
    db.commit()
    row=db.scalar(select(Video).where(Video.status=='queued',Video.details['mode'].as_string()=='transitions').order_by(Video.created_at).with_for_update(skip_locked=True).limit(1))
    if not row:
        return motion_id
    id=row.id;row.status='processing';row.updated_at=now();db.commit()
    try:
        photos=[storage.get(key) for key in row.assets['photos']]
        logo=storage.get(row.assets['logo']) if row.assets.get('logo') else None
        with tempfile.TemporaryDirectory(prefix='postready-video-') as directory:
            output=video_render.render(photos,row.details['products'],row.details,directory,logo)
            music=storage.get(row.assets['music']) if row.assets.get('music') else None
            preset=row.details.get('music','none')
            if preset in video_audio.PRESETS:
                music=(video_audio.MUSIC_ROOT/(preset+'.wav')).read_bytes()
            voice=storage.get(row.assets['voice']) if row.assets.get('voice') else None
            output=video_audio.compose(output,row.details['duration'],directory,music,voice)
        key=prefix(row)+'video.mp4';storage.put(key,output,'video/mp4')
        row.output_key=key;row.status='ready';row.expires_at=now()+timedelta(days=7);row.error=None
        row.updated_at=now();db.commit()
    except Exception:
        db.rollback();row=db.get(Video,id);row.status='failed';row.error='Could not create your video. Your form is available to try again.';row.updated_at=now();db.commit()
    return id

def cleanup_videos(db):
    rows=db.scalars(select(Video).where((Video.expires_at<=now())|((Video.status=='failed')&(Video.updated_at<=now()-timedelta(days=1)))|((Video.status=='uncertain')&(Video.updated_at<=now()-timedelta(days=7))))).all()
    count=0
    for row in rows:
        try:
            storage.remove_prefix(prefix(row));db.delete(row);db.commit();count+=1
        except Exception:
            db.rollback()
    return count
