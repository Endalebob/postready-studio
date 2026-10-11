import os
from celery import Celery
from sqlalchemy.orm import Session
from .database import engine
from .ads import cleanup
from .telegram import poll_updates, process_publish

celery = Celery('postready', broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'))
celery.conf.update(timezone='UTC', task_ignore_result=True, broker_connection_retry_on_startup=True,
                   beat_schedule={'expired-ads': {'task': 'postready.cleanup', 'schedule': 300.0},
                                  'telegram-updates': {'task': 'postready.telegram_updates', 'schedule': 15.0},
                                  'telegram-posts': {'task': 'postready.telegram_posts', 'schedule': 5.0}})

@celery.task(name='postready.cleanup')
def expired_ads():
    with Session(engine()) as db:
        return cleanup(db)

@celery.task(name='postready.telegram_updates')
def telegram_updates():
    with Session(engine()) as db:
        return poll_updates(db)

@celery.task(name='postready.telegram_posts')
def telegram_posts():
    with Session(engine()) as db:
        return process_publish(db)
