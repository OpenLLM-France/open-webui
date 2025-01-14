from celery import Celery
import os

celery = Celery(
    'queue_manager',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379'),
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_log_level='DEBUG',
    task_track_started=True,
    task_publish_retry=True,
    task_always_eager=False,
    task_eager_propagates=False,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_send_sent_event=True,
    task_remote_tracebacks=True,
    task_store_errors_even_if_ignored=True,
    task_ignore_result=False,
    worker_max_tasks_per_child=1000,
    broker_connection_retry=True,
    broker_connection_max_retries=None,
) 

@celery.task(name='auto_expiration')
def auto_expiration(ttl, timer_type, user_id):
    return True 