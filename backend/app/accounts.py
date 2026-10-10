import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator, model_validator
from pwdlib import PasswordHash
from sqlalchemy import JSON, DateTime, ForeignKey, String, delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column
from .database import Base, database
from .schemas import Contact
from typing import Literal

router = APIRouter()
hasher = PasswordHash.recommended()
dummy_hash = hasher.hash(secrets.token_urlsafe(32))


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))


class LoginSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Profile(Base):
    __tablename__ = 'profiles'
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
    logo_key: Mapped[str | None] = mapped_column(String(200), nullable=True)


class AuthAttempt(Base):
    __tablename__ = 'auth_attempts'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int]
    reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Registration(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    email: str = Field(max_length=254)
    password: str = Field(min_length=10, max_length=128)
    password_confirmation: str = Field(max_length=128)

    @field_validator('username')
    @classmethod
    def clean_username(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{3,40}', value):
            raise ValueError('Use 3–40 letters, numbers or underscores for your username.')
        return value

    @field_validator('email')
    @classmethod
    def clean_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Enter a valid email address.')
        return value

    @model_validator(mode='after')
    def matching(self):
        if self.password != self.password_confirmation:
            raise ValueError('Passwords must match.')
        return self


class Login(BaseModel):
    identifier: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class ProfileData(BaseModel):
    business_name: str = Field(min_length=1, max_length=100)
    address: str = Field(default='', max_length=160)
    contacts: list[Contact] = Field(min_length=1, max_length=4)
    language: Literal['am', 'en'] = 'am'
    theme: Literal['ethiopian-warmth', 'bold-contrast', 'clean-modern'] = 'ethiopian-warmth'

    @model_validator(mode='after')
    def nonempty(self):
        if not self.business_name.strip() or any(not c.kind.strip() or not c.value.strip() for c in self.contacts):
            raise ValueError('Business name and contact information are required.')
        return self


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def now():
    return datetime.now(timezone.utc)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def current_user(request: Request, db: Session = Depends(database)):
    token = request.cookies.get('postready_session', '')
    session = db.get(LoginSession, digest(token)) if token else None
    if not session or aware(session.expires_at) <= now():
        raise HTTPException(401, 'Please sign in to continue.')
    user = db.get(User, session.owner_id)
    if not user:
        raise HTTPException(401, 'Please sign in to continue.')
    return user


def check_rate(db, request, identifier):
    # Durable per-IP and per-identifier counters work across API restarts.
    host = request.client.host if request.client else 'unknown'
    for value, limit in [(host, 30), (identifier.strip().lower(), 10)]:
        key = digest(('ip:' if value == host else 'account:') + value)
        row = db.scalar(select(AuthAttempt).where(AuthAttempt.key == key).with_for_update())
        if row is None:
            row = AuthAttempt(key=key, count=0, reset_at=now()+timedelta(minutes=15))
            db.add(row)
        elif aware(row.reset_at) <= now():
            row.count = 0
            row.reset_at = now()+timedelta(minutes=15)
        if row.count >= limit:
            db.commit()
            raise HTTPException(429, 'Too many attempts. Please try again later.')
        row.count += 1
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(429, 'Please try again shortly.')


def issue_session(db, response, user):
    import os
    token = secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=digest(token), owner_id=user.id, expires_at=now()+timedelta(days=7)))
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= now()))
    db.commit()
    response.set_cookie('postready_session', token, max_age=7*86400, httponly=True,
                        secure=os.getenv('COOKIE_SECURE', 'false').lower() == 'true', samesite='lax', path='/')
    return {'id': user.id, 'username': user.username}


@router.post('/auth/register')
def register(values: Registration, request: Request, response: Response, db: Session = Depends(database)):
    check_rate(db, request, values.email)
    import uuid
    user = User(id=str(uuid.uuid4()), username=values.username, email=values.email, password_hash=hasher.hash(values.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Could not create an account with those details.')
    return issue_session(db, response, user)


@router.post('/auth/login')
def login(values: Login, request: Request, response: Response, db: Session = Depends(database)):
    check_rate(db, request, values.identifier)
    value = values.identifier.strip().lower()
    user = db.scalar(select(User).where(or_(User.username == value, User.email == value)))
    valid = hasher.verify(values.password, user.password_hash if user else dummy_hash)
    if not user or not valid:
        raise HTTPException(401, 'Incorrect username/email or password.')
    return issue_session(db, response, user)


@router.get('/auth/me')
def me(user: User = Depends(current_user)):
    return {'id': user.id, 'username': user.username}


@router.post('/auth/logout')
def logout(request: Request, response: Response, db: Session = Depends(database)):
    db.execute(delete(LoginSession).where(LoginSession.token_hash == digest(request.cookies.get('postready_session', ''))))
    db.commit()
    response.delete_cookie('postready_session', path='/')
    return {'ok': True}


@router.get('/profile')
def get_profile(user: User = Depends(current_user), db: Session = Depends(database)):
    profile = db.get(Profile, user.id)
    return profile_view(profile) if profile else None


def profile_view(profile):
    return {**profile.data, 'logo_url': '/api/backend/profile/logo' if profile.logo_key else None}


@router.put('/profile')
def save_profile(values: ProfileData, user: User = Depends(current_user), db: Session = Depends(database)):
    profile = db.get(Profile, user.id)
    if profile is None:
        profile = Profile(owner_id=user.id, data=values.model_dump(), logo_key=None)
        db.add(profile)
    else:
        profile.data = values.model_dump()
    db.commit()
    return profile_view(profile)
