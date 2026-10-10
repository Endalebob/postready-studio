import os
from celery import Celery
from sqlalchemy.orm import Session
from .database import engine
from .ads import cleanup

celery = Celery('postready', broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'))
celery.conf.update(timezone='UTC', task_ignore_result=True, broker_connection_retry_on_startup=True,
                   beat_schedule={'expired-ads': {'task': 'postready.cleanup', 'schedule': 300.0}})

@celery.task(name='postready.cleanup')
def expired_ads():
    with Session(engine()) as db:
        return cleanup(db)
