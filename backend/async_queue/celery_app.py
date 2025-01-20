from celery import Celery

celery_app = Celery(
    'async_queue',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

# Configuration optionnelle
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
) 

@celery_app.task(name='auto_expiration')
def auto_expiration(ttl, timer_type, user_id):
    return True 