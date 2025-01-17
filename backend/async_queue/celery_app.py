from celery import Celery

celery = Celery(
    'app',
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    include=['app.queue_manager']
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_ignore_result=False
) 

@celery.task(name='auto_expiration')
def auto_expiration(ttl, timer_type, user_id):
    return True 