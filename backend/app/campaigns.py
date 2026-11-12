"""Paused campaign drafts. No generation, scheduling tasks or publishing side effects."""
import calendar
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from .accounts import User, current_user, now, aware
from .database import Base, database
from .gallery import GalleryAsset
from .telegram import Connection

from .accounts import admin_user
router = APIRouter(dependencies=[Depends(admin_user)])
MAX_DRAFTS = 10

class Campaign(Base):
    __tablename__ = 'campaigns'
    __table_args__ = (UniqueConstraint('owner_id', 'request_key', name='uq_campaign_owner_request'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    request_key: Mapped[str] = mapped_column(String(36))
    settings: Mapped[dict] = mapped_column(JSON)
    destination_title: Mapped[str] = mapped_column(String(255))
    revision: Mapped[int]
    deleted: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Schedule(BaseModel):
    model_config = {'extra': 'forbid'}
    frequency: Literal['daily', 'weekly', 'monthly'] = 'weekly'
    timezone: str = Field(default='Africa/Addis_Ababa', max_length=100)
    local_time: str = Field(pattern=r'^([01][0-9]|2[0-3]):[0-5][0-9]$')
    weekday: int | None = Field(default=None, ge=0, le=6, strict=True)
    day_of_month: int | None = Field(default=None, ge=1, le=31, strict=True)

    @field_validator('timezone')
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError('Choose a valid IANA timezone.')
        return value

    @model_validator(mode='after')
    def relevant_fields(self):
        if self.frequency == 'weekly' and self.weekday is None:
            raise ValueError('Choose a weekday for a weekly schedule.')
        if self.frequency == 'monthly' and self.day_of_month is None:
            raise ValueError('Choose a day of month for a monthly schedule.')
        if self.frequency != 'weekly':
            self.weekday = None
        if self.frequency != 'monthly':
            self.day_of_month = None
        return self

class Settings(BaseModel):
    model_config = {'extra': 'forbid'}
    name: str = Field(min_length=1, max_length=100)
    gallery_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    connection_id: uuid.UUID
    schedule: Schedule
    language: Literal['am', 'en'] = 'am'
    theme: Literal['ethiopian-warmth', 'bold-contrast', 'clean-modern'] = 'ethiopian-warmth'
    instructions: str = Field(default='', max_length=600)

    @field_validator('name')
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Enter a campaign name.')
        return value

    @field_validator('gallery_ids')
    @classmethod
    def unique_items(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('Select each product only once.')
        return value

class Create(BaseModel):
    model_config = {'extra': 'forbid'}
    request_key: uuid.UUID
    settings: Settings

class Change(BaseModel):
    model_config = {'extra': 'forbid'}
    revision: int = Field(ge=1, strict=True)
    settings: Settings

class Revision(BaseModel):
    model_config = {'extra': 'forbid'}
    revision: int = Field(ge=1, strict=True)

def occurrences(schedule: Schedule, after: datetime):
    """Local calendar recurrence; skip DST gaps and use the first fold only."""
    zone = ZoneInfo(schedule.timezone)
    after = aware(after)
    start = after.astimezone(zone).date()
    hour, minute = map(int, schedule.local_time.split(':'))
    result = []
    for offset in range(400):
        day = start + timedelta(days=offset)
        if schedule.frequency == 'weekly' and day.weekday() != schedule.weekday:
            continue
        if schedule.frequency == 'monthly' and day.day != min(schedule.day_of_month, calendar.monthrange(day.year, day.month)[1]):
            continue
        wall = datetime(day.year, day.month, day.day, hour, minute)
        local = wall.replace(tzinfo=zone, fold=0)
        utc = local.astimezone(timezone.utc)
        if utc.astimezone(zone).replace(tzinfo=None) != wall or utc <= after:
            continue
        result.append({'local': local.isoformat(), 'utc': utc.isoformat()})
        if len(result) == 3:
            return result
    raise HTTPException(422, 'Could not calculate this schedule. Choose another timezone or time.')

def owned(db, owner, id, lock=False):
    query = select(Campaign).where(Campaign.id == id, Campaign.owner_id == owner, Campaign.deleted == False)
    row = db.scalar(query.with_for_update() if lock else query)
    if not row:
        raise HTTPException(404, 'Campaign not found.')
    return row

def eligible(row):
    return bool(row and row.ready and row.active and row.approved_at and not row.deleted)

def references(db, owner, settings, lock=False):
    query = select(Connection).where(Connection.owner_id == owner)
    connection = db.scalar(query.with_for_update() if lock else query)
    destination_ok = bool(connection and connection.active and connection.chat_id and connection.telegram_user_id and connection.connection_id == str(settings.connection_id))
    query = select(GalleryAsset).where(GalleryAsset.owner_id == owner, GalleryAsset.id.in_([str(id) for id in settings.gallery_ids])).order_by(GalleryAsset.id)
    products = {row.id: row for row in db.scalars(query.with_for_update() if lock else query)}
    missing = [str(id) for id in settings.gallery_ids if not eligible(products.get(str(id)))]
    return connection, destination_ok, missing

def view(db, row):
    settings = Settings.model_validate(row.settings)
    _, destination_ok, missing = references(db, row.owner_id, settings)
    return {'id': row.id, 'settings': row.settings, 'status': 'paused', 'approval_mode': 'review',
            'destination_title': row.destination_title, 'revision': row.revision,
            'warnings': ([] if destination_ok else ['Reconnect or select a verified Telegram channel before saving.']) +
                        ([] if not missing else [f'{len(missing)} selected product(s) are missing, inactive or need approval.']),
            'unavailable_gallery_ids': missing, 'destination_available': destination_ok,
            'preview': occurrences(settings.schedule, now()), 'created_at': aware(row.created_at).isoformat(),
            'updated_at': aware(row.updated_at).isoformat()}

def validate_references(db, owner, settings):
    connection, valid, missing = references(db, owner, settings, True)
    if not valid:
        raise HTTPException(409, 'Choose your currently verified Telegram channel. Reconnect it in Social channels if needed.')
    if missing:
        raise HTTPException(409, 'Select only your active, approved gallery products. Refresh the products and review your selection.')
    return connection

@router.get('/campaigns/options')
def options(user: User = Depends(current_user)):
    return {'timezones': sorted(available_timezones()), 'max_drafts': MAX_DRAFTS}

@router.post('/campaigns/preview')
def preview(schedule: Schedule, user: User = Depends(current_user)):
    return {'preview': occurrences(schedule, now())}

@router.get('/campaigns')
def library(user: User = Depends(current_user), db: Session = Depends(database)):
    rows = db.scalars(select(Campaign).where(Campaign.owner_id == user.id, Campaign.deleted == False).order_by(Campaign.created_at.desc()).limit(MAX_DRAFTS))
    return [view(db, row) for row in rows]

@router.post('/campaigns')
def create(values: Create, user: User = Depends(current_user), db: Session = Depends(database)):
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    existing = db.scalar(select(Campaign).where(Campaign.owner_id == user.id, Campaign.request_key == str(values.request_key)))
    if existing:
        if existing.deleted:
            raise HTTPException(410, 'This draft was deleted. Start a new draft.')
        return view(db, existing)
    if db.scalar(select(func.count()).select_from(Campaign).where(Campaign.owner_id == user.id, Campaign.deleted == False)) >= MAX_DRAFTS:
        raise HTTPException(409, 'You can save up to 10 campaign drafts. Delete one before adding another.')
    connection = validate_references(db, user.id, values.settings)
    row = Campaign(id=str(uuid.uuid4()), owner_id=user.id, request_key=str(values.request_key),
                   settings=values.settings.model_dump(mode='json'), destination_title=connection.title or 'Telegram channel',
                   revision=1, deleted=False, created_at=now(), updated_at=now())
    db.add(row); db.commit()
    return view(db, row)

@router.get('/campaigns/{id}')
def get_item(id: str, user: User = Depends(current_user), db: Session = Depends(database)):
    return view(db, owned(db, user.id, id))

@router.put('/campaigns/{id}')
def edit(id: str, values: Change, user: User = Depends(current_user), db: Session = Depends(database)):
    row = owned(db, user.id, id, True)
    if row.revision != values.revision:
        raise HTTPException(409, 'This campaign changed in another tab. Reopen it before saving.')
    connection = validate_references(db, user.id, values.settings)
    row.settings = values.settings.model_dump(mode='json'); row.destination_title = connection.title or 'Telegram channel'
    row.revision += 1; row.updated_at = now(); db.commit()
    return view(db, row)

@router.delete('/campaigns/{id}')
def delete_item(id: str, values: Revision, user: User = Depends(current_user), db: Session = Depends(database)):
    row = owned(db, user.id, id, True)
    if row.revision != values.revision:
        raise HTTPException(409, 'This campaign changed in another tab. Reopen it before deleting.')
    row.deleted = True; row.revision += 1; row.updated_at = now(); db.commit()
    return {'ok': True}
