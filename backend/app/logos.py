import io
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session
from .accounts import Profile, User, current_user, profile_view
from .database import database
from . import storage

router = APIRouter()
MAX_LOGO = 2*1024*1024


def normalize_logo(data):
    if len(data) > MAX_LOGO:
        raise HTTPException(413, 'Choose a logo smaller than 2 MB.')
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in ('PNG', 'JPEG', 'WEBP') or image.width*image.height > 4_000_000:
                raise HTTPException(415, 'Choose a PNG, JPEG or WebP logo up to 4 megapixels.')
            image = ImageOps.exif_transpose(image).convert('RGBA')
            image.thumbnail((512, 512))
            output = io.BytesIO()
            image.save(output, format='PNG')
            return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(415, 'We could not read this logo. Choose another image.')


@router.put('/profile/logo')
def upload_logo(logo: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(database)):
    profile = db.get(Profile, user.id)
    if profile is None:
        raise HTTPException(409, 'Save your business profile first.')
    try:
        image = normalize_logo(logo.file.read(MAX_LOGO+1))
    finally:
        logo.file.close()
    key = f'logos/{user.id}/{uuid.uuid4()}.png'
    try:
        storage.put(key, image)
    except Exception:
        raise HTTPException(503, 'Could not save your logo. Please try again.')
    old_key = profile.logo_key
    profile.logo_key = key
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            storage.remove(key)
        except Exception:
            pass
        raise HTTPException(503, 'Could not save your logo. Please try again.')
    if old_key:
        try:
            storage.remove(old_key)
        except Exception:
            pass  # A later asset cleanup pass may reclaim an unreferenced object.
    return profile_view(profile)


@router.get('/profile/logo')
def read_logo(user: User = Depends(current_user), db: Session = Depends(database)):
    profile = db.get(Profile, user.id)
    if not profile or not profile.logo_key:
        raise HTTPException(404, 'No logo saved.')
    try:
        data = storage.get(profile.logo_key)
    except Exception:
        raise HTTPException(503, 'Could not load your logo. Please try again.')
    return Response(data, media_type='image/png', headers={'Cache-Control': 'private, no-store'})


@router.delete('/profile/logo')
def delete_logo(user: User = Depends(current_user), db: Session = Depends(database)):
    profile = db.get(Profile, user.id)
    if profile and profile.logo_key:
        try:
            storage.remove(profile.logo_key)
        except Exception:
            raise HTTPException(503, 'Could not remove your logo. Please try again.')
        profile.logo_key = None
        db.commit()
    return profile_view(profile) if profile else None
