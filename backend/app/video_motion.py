"""Durable paid-task workflow, one short worker action per dispatch."""
import copy
import tempfile
from datetime import timedelta
from sqlalchemy import select, or_, and_
from .accounts import now, aware
from . import storage, video_providers, video_render, video_audio

def advance(db):
    from .videos import Video, prefix
    cutoff=now()-timedelta(minutes=10)
    # A crash between sending and saving a provider ID is never blindly resubmitted.
    for row in db.scalars(select(Video).where(Video.status=='submitting',Video.updated_at<cutoff).with_for_update(skip_locked=True)).all():
        row.status='uncertain';row.error='Provider submission was interrupted. Check its dashboard before creating another video.';row.updated_at=now()
    db.commit()
    row=db.scalar(select(Video).where(Video.details['mode'].as_string()=='motion',or_(
        Video.status=='queued',and_(Video.status=='generating',Video.updated_at<now()-timedelta(seconds=5)),
        and_(Video.status=='processing',Video.updated_at<cutoff))).order_by(Video.updated_at).with_for_update(skip_locked=True).limit(1))
    if not row:
        return None
    id=row.id;row.status='processing';row.updated_at=now();db.commit()
    provider=row.details['provider'];assets=copy.deepcopy(row.assets);tasks=assets.setdefault('tasks',[])
    count=1 if provider=='bfl' else len(assets['photos'])
    try:
        if aware(row.created_at)<now()-timedelta(hours=2):
            raise video_providers.ProviderFailure('This provider task took too long. Check its dashboard before creating another video.')
        if tasks and not tasks[-1].get('asset'):
            task=tasks[-1]
            result=video_providers.poll(provider,task)
            if result:
                data=video_providers.download(provider,result)
                asset=prefix(row)+f'motion/{len(tasks)-1}.mp4';storage.put(asset,data,'video/mp4');task['asset']=asset
            row.assets=assets;row.status='generating';row.updated_at=now();db.commit()
        elif len(tasks)<count:
            photos=[storage.get(k) for k in assets['photos']] if provider=='bfl' else [storage.get(assets['photos'][len(tasks)])]
            # Commit the pre-send marker before the paid HTTP request.
            row.status='submitting';row.updated_at=now();db.commit()
            duration=row.details['duration'] if count==1 else 4
            task=video_providers.submit(provider,photos,duration,row.details['theme'])
            tasks.append(task);row.assets=assets;row.status='generating';row.updated_at=now();db.commit()
        else:
            clips=[storage.get(t['asset']) for t in tasks]
            photos=[storage.get(k) for k in assets['photos']]
            logo=storage.get(assets['logo']) if assets.get('logo') else None
            music=storage.get(assets['music']) if assets.get('music') else None
            preset=row.details.get('music','none')
            if preset in video_audio.PRESETS:
                music=(video_audio.MUSIC_ROOT/(preset+'.wav')).read_bytes()
            voice=storage.get(assets['voice']) if assets.get('voice') else None
            with tempfile.TemporaryDirectory(prefix='postready-motion-') as directory:
                output=video_render.motion(clips,photos,row.details['products'],row.details,directory,logo)
                output=video_audio.compose(output,row.details['duration'],directory,music,voice)
            output_key=prefix(row)+'video.mp4';storage.put(output_key,output,'video/mp4')
            row.output_key=output_key;row.status='ready';row.expires_at=now()+timedelta(days=7);row.error=None;row.updated_at=now();db.commit()
    except video_providers.UncertainSubmission as exc:
        db.rollback();row=db.get(Video,id);row.status='uncertain';row.error=str(exc);row.updated_at=now();db.commit()
    except video_providers.ProviderFailure as exc:
        db.rollback();row=db.get(Video,id);row.status='failed';row.error=str(exc);row.updated_at=now();db.commit()
    except Exception:
        db.rollback();row=db.get(Video,id)
        if row.status=='submitting':
            row.status='uncertain';row.error='The provider outcome could not be saved. Check its dashboard before creating another video.'
        elif aware(row.created_at)<now()-timedelta(hours=2):
            row.status='failed';row.error='Could not finish this provider task. Check its dashboard before trying again.'
        else:
            # Polling, download and local composition can safely resume with the saved IDs.
            row.status='generating'
        row.updated_at=now();db.commit()
    return id
