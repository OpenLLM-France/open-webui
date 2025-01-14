from celery import Celery
import os

def setup_test_celery():
    """Configure Celery pour les tests en mode asynchrone."""
    # Récupération des variables d'environnement Redis
    redis_host = os.getenv('REDIS_HOST', 'localhost')  # localhost en local
        
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    redis_db = int(os.getenv('REDIS_DB', 1))
    
    broker_url = f'redis://{redis_host}:{redis_port}/{redis_db}'
    backend_url = f'redis://{redis_host}:{redis_port}/{redis_db}'
    
    print(f"Configuration Celery avec: host={redis_host}, port={redis_port}, db={redis_db}")
    print(f"Broker URL: {broker_url}")
    print(f"Backend URL: {backend_url}")
    
    celery_app = Celery(
        'test_app',
        broker=broker_url,
        backend=backend_url
    )
    
    celery_app.conf.update({
        'broker_url': broker_url,
        'result_backend': backend_url,
        'task_always_eager': False,  # Désactiver le mode eager pour une vraie exécution async
        'task_eager_propagates': False,
        'worker_prefetch_multiplier': 1,
        'task_acks_late': False,
        'task_track_started': True,
        'task_send_sent_event': True,
        'task_remote_tracebacks': True,
        'task_store_errors_even_if_ignored': True,
        'task_ignore_result': False,
        'worker_concurrency': 1,  # Un seul worker pour les tests
        'broker_connection_retry': True,  # Activer les retry
        'broker_connection_max_retries': None,  # Retry indéfiniment
    })
    
    return celery_app 