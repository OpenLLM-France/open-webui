import pytest
from celery import Celery
import asyncio
import logging
from app.queue_manager import celery

@celery.task(name="simple_test_task")
async def simple_test_task(message: str, sleep_time: float = 0.1):
    """Tâche de test simple qui log un message et attend un peu."""
    logger = logging.getLogger('celery_test_logger')
    logger.info(f"Début de test_task avec message: {message}")
    await asyncio.sleep(sleep_time)
    logger.info(f"Fin de test_task avec message: {message}")
    return f"Terminé: {message}"

@pytest.mark.asyncio
async def test_celery_eager_mode(celery_app, celery_logger):
    """Test pour vérifier que le mode eager fonctionne correctement."""
    celery_logger.info("Démarrage du test du mode eager")
    
    # Vérifier la configuration
    assert celery_app.conf.task_always_eager is True, "Le mode eager n'est pas activé"
    celery_logger.info(f"Mode eager vérifié: {celery_app.conf.task_always_eager}")
    
    # Exécuter la tâche de manière synchrone
    message = "Test synchrone"
    celery_logger.info(f"Exécution de la tâche avec message: {message}")
    
    result = await simple_test_task.apply(args=[message]).get()
    celery_logger.info(f"Résultat de la tâche: {result}")
    
    assert result == f"Terminé: {message}", "La tâche n'a pas retourné le bon résultat"
    celery_logger.info("Test du mode eager terminé avec succès")

@pytest.mark.asyncio
async def test_celery_task_chaining(celery_app, celery_logger):
    """Test pour vérifier que les tâches peuvent s'appeler entre elles."""
    celery_logger.info("Démarrage du test de chaînage de tâches")
    
    # Exécuter une séquence de tâches
    messages = ["Premier", "Deuxième", "Troisième"]
    results = []
    
    for msg in messages:
        celery_logger.info(f"Exécution de la tâche {msg}")
        result = await simple_test_task.apply(args=[msg, 0.1]).get()
        results.append(result)
        celery_logger.info(f"Résultat obtenu: {result}")
    
    # Vérifier les résultats
    assert len(results) == len(messages), "Nombre incorrect de résultats"
    for msg, res in zip(messages, results):
        assert res == f"Terminé: {msg}", f"Résultat incorrect pour {msg}"
    
    celery_logger.info("Test de chaînage terminé avec succès")

@pytest.mark.asyncio
async def test_celery_error_handling(celery_app, celery_logger):
    """Test pour vérifier la gestion des erreurs dans les tâches."""
    celery_logger.info("Démarrage du test de gestion d'erreurs")
    
    @celery_app.task(name="failing_task")
    async def failing_task():
        celery_logger.info("Démarrage de la tâche qui va échouer")
        raise ValueError("Erreur de test")
    
    # Vérifier que l'erreur est bien propagée
    with pytest.raises(ValueError) as excinfo:
        celery_logger.info("Exécution de la tâche qui doit échouer")
        await failing_task.apply().get()
    
    assert str(excinfo.value) == "Erreur de test", "L'erreur n'a pas été propagée correctement"
    celery_logger.info("Test de gestion d'erreurs terminé avec succès") 