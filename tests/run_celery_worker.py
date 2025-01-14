import os
from celery import Celery

def run_celery():
    """Configure et démarre un worker Celery pour les tests."""
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    
    app = Celery(
        'test_worker',
        broker=f'redis://{redis_host}:{redis_port}',
        backend=f'redis://{redis_host}:{redis_port}'
    )
    
    app.conf.update({
        'broker_url': f'redis://{redis_host}:{redis_port}',
        'result_backend': f'redis://{redis_host}:{redis_port}',
        'task_serializer': 'json',
        'result_serializer': 'json',
        'accept_content': ['json'],
        'enable_utc': True,
    })
    
    app.worker_main(['worker', '--loglevel=INFO'])

if __name__ == '__main__':
    run_celery() 