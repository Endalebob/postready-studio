import hashlib
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column
from .database import Base
from .accounts import current_user, database, User, now, aware
from .ads import Ad, AdRevision, owned
from . import storage, telegram_api as provider

router = APIRouter()

class Connection(Base):
    __tablename__ = 'telegram_connections'
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    connection_id: Mapped[str] = mapped_column(String(36))
    active: Mapped[bool] = mapped_column(default=False)
    challenge_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    challenge_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    telegram_user_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    observed_chat: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    chat_id: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(String(255), nullable=True)

class BotState(Base):
    __tablename__ = 'telegram_bot_state'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    offset: Mapped[int]

class PublishAttempt(Base):
    __tablename__ = 'publish_attempts'
    __table_args__ = (UniqueConstraint('owner_id','ad_id','revision','connection_id',name='uq_publish_revision_destination'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    ad_id: Mapped[str | None] = mapped_column(ForeignKey('ads.id', ondelete='SET NULL'), nullable=True)
    revision: Mapped[int]
    connection_id: Mapped[str] = mapped_column(String(36))
    chat_id: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    message_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

class Confirm(BaseModel):
    confirmed: bool

class Publish(Confirm):
    revision: int = Field(ge=1)
    connection_id: str = Field(max_length=36)

def connection_view(row):
    return {'configured': provider.configured(), 'active': bool(row and row.active),
            'connection_id': row.connection_id if row else None,
            'title': row.title if row and row.active else None, 'username': row.username if row and row.active else None,
            'identity_verified': bool(row and row.telegram_user_id),
            'observed_channel': row.observed_chat if row and not row.active else None,
            'challenge_expires': aware(row.challenge_expires).isoformat() if row and row.challenge_expires else None,
            'checked_at': aware(row.checked_at).isoformat() if row and row.checked_at else None,
            'error': row.error if row else None}

def attempt_view(row):
    link = None
    if row.message_id:
        if row.username and re.fullmatch(r'[A-Za-z0-9_]+', row.username):
            link = f'https://t.me/{row.username}/{row.message_id}'
        elif row.chat_id.startswith('-100'):
            link = f'https://t.me/c/{row.chat_id[4:]}/{row.message_id}'
    return {'id': row.id, 'revision': row.revision, 'connection_id': row.connection_id, 'status': row.status, 'detail': row.detail,
            'title': row.title, 'message_id': row.message_id, 'link': link, 'created_at': aware(row.created_at).isoformat()}

@router.get('/telegram/connection')
def connection(user: User = Depends(current_user), db: Session = Depends(database)):
    return connection_view(db.get(Connection, user.id))

@router.post('/telegram/challenge')
def challenge(user: User = Depends(current_user), db: Session = Depends(database)):
    if not provider.configured():
        raise HTTPException(503, 'Telegram is not configured yet.')
    row = db.get(Connection, user.id)
    if row and row.active:
        raise HTTPException(409, 'Disconnect the current channel before connecting another.')
    try:
        me = provider.bot()
        if provider.call('getWebhookInfo').get('url'):
            raise provider.TelegramRejected('Use a dedicated bot without an existing webhook for local polling.')
    except (provider.TelegramRejected, provider.TelegramUncertain) as exc:
        raise HTTPException(503, str(exc))
    code = secrets.token_urlsafe(24)
    if row is None:
        row = Connection(owner_id=user.id)
        db.add(row)
    row.connection_id = str(uuid.uuid4())
    row.active = False
    row.challenge_hash = hashlib.sha256(code.encode()).hexdigest()
    row.challenge_expires = now()+timedelta(minutes=20)
    row.telegram_user_id = None
    row.observed_chat = None
    row.chat_id = None
    row.error = None
    db.commit()
    return {**connection_view(row), 'command': '/postready_connect '+code,
            'bot_username': me['username'], 'start_url': 'https://t.me/'+me['username']+'?start='+code}

@router.post('/telegram/connect')
def connect(values: Confirm, user: User = Depends(current_user), db: Session = Depends(database)):
    row = db.scalar(select(Connection).where(Connection.owner_id == user.id).with_for_update())
    if row and row.active:
        return connection_view(row)
    if not values.confirmed or not row or not row.challenge_expires or aware(row.challenge_expires) <= now() or not row.telegram_user_id or not row.observed_chat:
        raise HTTPException(409, 'Complete the Telegram identity and channel checks before confirming.')
    try:
        chat = provider.verify_channel(row.observed_chat['id'], row.telegram_user_id)
    except (provider.TelegramRejected, provider.TelegramUncertain) as exc:
        raise HTTPException(409, str(exc))
    row.chat_id = str(chat['id'])
    row.title = chat.get('title','Telegram channel')[:255]
    row.username = chat.get('username')
    row.active = True
    row.challenge_hash = None
    row.challenge_expires = None
    row.observed_chat = None
    row.checked_at = now()
    row.error = None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'This channel is already connected to another account.')
    return connection_view(row)

@router.delete('/telegram/connection')
def disconnect(user: User = Depends(current_user), db: Session = Depends(database)):
    row = db.scalar(select(Connection).where(Connection.owner_id == user.id).with_for_update())
    if row:
        db.execute(update(PublishAttempt).where(PublishAttempt.owner_id == user.id, PublishAttempt.status == 'queued')
                   .values(status='failed', detail='Channel disconnected before publishing.', updated_at=now()))
        row.active = False
        row.chat_id = None
        row.challenge_hash = None
        row.challenge_expires = None
        row.observed_chat = None
        row.telegram_user_id = None
        row.error = None
        db.commit()
    return {'ok': True}

@router.post('/telegram/check')
def check_permissions(user: User = Depends(current_user), db: Session = Depends(database)):
    row = ready_connection(db,user.id)
    try:
        provider.verify_channel(row.chat_id,row.telegram_user_id)
        row.error = None
    except provider.TelegramRejected as exc:
        row.active = False
        row.error = str(exc)
    except provider.TelegramUncertain:
        row.error = 'Could not verify Telegram permissions right now. Please check again.'
    row.checked_at = now()
    db.commit()
    return connection_view(row)

def poll_updates(db):
    if not provider.configured():
        return 0
    key = hashlib.sha256(os.environ['TELEGRAM_BOT_TOKEN'].encode()).hexdigest()
    if db.get(BotState, key) is None:
        db.add(BotState(key=key, offset=0))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    state = db.scalar(select(BotState).where(BotState.key == key).with_for_update(skip_locked=True))
    if state is None:
        return 0
    try:
        updates = provider.call('getUpdates', {'offset': state.offset, 'timeout': 10, 'allowed_updates': json.dumps(['message','channel_post'])})
        for item in updates:
            state.offset = max(state.offset, item['update_id']+1)
            message = item.get('message') or item.get('channel_post') or {}
            text = message.get('text','')
            match = re.fullmatch(r'/(?:start|postready_connect)(?:@[A-Za-z0-9_]+)? ([A-Za-z0-9_-]{32})', text.strip())
            if not match or message.get('forward_origin'):
                continue
            row = db.scalar(select(Connection).where(Connection.challenge_hash == hashlib.sha256(match.group(1).encode()).hexdigest()).with_for_update())
            if not row or row.active or not row.challenge_expires or aware(row.challenge_expires) <= now():
                continue
            chat = message.get('chat',{})
            if chat.get('type') == 'private' and text.startswith('/start'):
                sender = message.get('from',{})
                if sender.get('id') and not sender.get('is_bot') and not row.telegram_user_id:
                    row.telegram_user_id = str(sender['id'])
            elif chat.get('type') == 'channel' and text.startswith('/postready_connect') and not row.observed_chat:
                row.observed_chat = {'id': str(chat['id']), 'title': chat.get('title','Telegram channel'), 'username': chat.get('username')}
        db.commit()
        return len(updates)
    except Exception:
        db.rollback()
        return 0

def ready_connection(db, owner, connection_id=None):
    if not provider.configured():
        raise HTTPException(503, 'Telegram is not configured yet.')
    row = db.get(Connection, owner)
    if not row or not row.active or (connection_id and row.connection_id != connection_id):
        raise HTTPException(409, 'Connect a Telegram channel before publishing.')
    return row

def saved_revision(db, owner, ad_id, revision):
    ad = owned(db, owner, ad_id)
    record = db.get(AdRevision, (ad.id, revision))
    if not record:
        raise HTTPException(409, 'Save the advertisement before publishing.')
    if len(record.payload['social_caption'].encode('utf-16-le'))//2 > 1024:
        raise HTTPException(422, 'Shorten the caption to 1024 characters before publishing to Telegram.')
    return ad, record

@router.get('/ads/{ad_id}/publish-preview')
def preview(ad_id: str, revision: int, user: User = Depends(current_user), db: Session = Depends(database)):
    ad, record = saved_revision(db,user.id,ad_id,revision)
    row = ready_connection(db,user.id)
    return {'revision': revision, 'connection_id': row.connection_id, 'title': row.title,
            'caption': record.payload['social_caption'], 'image_url': f'/api/backend/ads/{ad_id}/revisions/{revision}/png'}

@router.get('/ads/{ad_id}/revisions/{revision}/png')
def revision_png(ad_id: str, revision: int, user: User = Depends(current_user), db: Session = Depends(database)):
    ad = owned(db,user.id,ad_id)
    record = db.get(AdRevision,(ad.id,revision))
    if not record:
        raise HTTPException(404, 'Saved revision not found.')
    try:
        data = storage.get(record.png_key)
    except Exception:
        raise HTTPException(503, 'Could not load the saved image. Please try again.')
    if aware(ad.expires_at) <= now():
        raise HTTPException(410, 'This advertisement has expired.')
    return Response(data,media_type='image/png')

@router.post('/ads/{ad_id}/publish')
def publish(ad_id: str, values: Publish, user: User = Depends(current_user), db: Session = Depends(database)):
    if not values.confirmed:
        raise HTTPException(422, 'Review and confirm the post before publishing.')
    ad, record = saved_revision(db,user.id,ad_id,values.revision)
    if ad.revision != values.revision:
        raise HTTPException(409, 'This advertisement has changed. Reopen and review its latest saved revision.')
    row = ready_connection(db,user.id,values.connection_id)
    existing = db.scalar(select(PublishAttempt).where(PublishAttempt.owner_id == user.id, PublishAttempt.ad_id == ad_id,
                         PublishAttempt.revision == values.revision, PublishAttempt.connection_id == row.connection_id))
    if existing:
        return attempt_view(existing)
    attempt = PublishAttempt(id=str(uuid.uuid4()),owner_id=user.id,ad_id=ad_id,revision=values.revision,
                connection_id=row.connection_id,chat_id=row.chat_id,title=row.title,username=row.username,
                status='queued',detail=None,created_at=now(),updated_at=now(),message_id=None)
    destination_id = row.connection_id
    db.add(attempt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        attempt = db.scalar(select(PublishAttempt).where(PublishAttempt.owner_id == user.id,PublishAttempt.ad_id == ad_id,
                       PublishAttempt.revision == values.revision,PublishAttempt.connection_id == destination_id))
        if attempt is None:
            raise HTTPException(409, 'The destination changed. Review your post again.')
    return attempt_view(attempt)

@router.get('/ads/{ad_id}/publishes')
def publishes(ad_id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    owned(db,user.id,ad_id)
    return [attempt_view(row) for row in db.scalars(select(PublishAttempt).where(PublishAttempt.owner_id == user.id,PublishAttempt.ad_id == ad_id).order_by(PublishAttempt.created_at.desc())).all()]

@router.get('/publishes/{attempt_id}')
def publish_status(attempt_id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    row = db.scalar(select(PublishAttempt).where(PublishAttempt.id == attempt_id,PublishAttempt.owner_id == user.id))
    if not row:
        raise HTTPException(404, 'Publishing attempt not found.')
    return attempt_view(row)

@router.post('/publishes/{attempt_id}/retry')
def retry_publish(attempt_id: str, values: Confirm, user: User = Depends(current_user), db: Session = Depends(database)):
    row = db.scalar(select(PublishAttempt).where(PublishAttempt.id == attempt_id,PublishAttempt.owner_id == user.id).with_for_update())
    if not row:
        raise HTTPException(404, 'Publishing attempt not found.')
    if not values.confirmed or row.status != 'failed':
        raise HTTPException(409, 'Only a confirmed failed attempt can be retried.')
    if not row.ad_id:
        raise HTTPException(410, 'This advertisement is no longer available.')
    saved_revision(db,user.id,row.ad_id,row.revision)
    ready_connection(db,user.id,row.connection_id)
    row.status = 'queued'
    row.detail = None
    row.updated_at = now()
    db.commit()
    return attempt_view(row)

def finish(db, attempt, status, detail=None):
    attempt.status = status
    attempt.detail = detail
    attempt.updated_at = now()
    db.commit()

def process_publish(db):
    # A crash after submission may have sent a post. Never automatically resend it.
    db.execute(update(PublishAttempt).where(PublishAttempt.status == 'publishing',PublishAttempt.updated_at <= now()-timedelta(minutes=5))
               .values(status='unknown',detail='Telegram may have received this post. Check your channel before making another post.',updated_at=now()))
    db.commit()
    attempt = db.scalar(select(PublishAttempt).where(PublishAttempt.status == 'queued').order_by(PublishAttempt.created_at).with_for_update(skip_locked=True).limit(1))
    if not attempt:
        return None
    attempt_id = attempt.id
    finish(db,attempt,'publishing')
    try:
        if not attempt.ad_id:
            raise HTTPException(410, 'This advertisement is no longer available.')
        ad, record = saved_revision(db,attempt.owner_id,attempt.ad_id,attempt.revision)
        row = ready_connection(db,attempt.owner_id,attempt.connection_id)
        provider.verify_channel(attempt.chat_id,row.telegram_user_id)
        png = storage.get(record.png_key)
        caption = record.payload['social_caption']
        db.expire_all()
        # Recheck ownership, connection and deadline immediately before submission.
        owned(db,attempt.owner_id,attempt.ad_id)
        ready_connection(db,attempt.owner_id,attempt.connection_id)
    except HTTPException as exc:
        finish(db,attempt,'failed',str(exc.detail))
        return attempt_id
    except (provider.TelegramRejected,provider.TelegramUncertain) as exc:
        if isinstance(exc,provider.TelegramRejected):
            connection = db.get(Connection,attempt.owner_id)
            if connection and connection.connection_id == attempt.connection_id:
                connection.active = False
                connection.error = str(exc)
                connection.checked_at = now()
        finish(db,attempt,'failed',str(exc))
        return attempt_id
    except Exception:
        finish(db,attempt,'failed','Could not prepare the saved post. Please retry after checking your connection.')
        return attempt_id
    try:
        message = provider.send_photo(attempt.chat_id,png,caption)
        attempt.message_id = str(message['message_id'])
        finish(db,attempt,'published')
    except provider.TelegramRejected as exc:
        finish(db,attempt,'failed',str(exc))
    except Exception:
        db.rollback()
        attempt = db.get(PublishAttempt,attempt_id)
        finish(db,attempt,'unknown','Telegram may have received this post. Check your channel before making another post.')
    return attempt_id
