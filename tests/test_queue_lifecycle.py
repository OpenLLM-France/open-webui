import os
import pytest
import redis.asyncio as redis
import logging
import asyncio
from app.queue_manager import QueueManager

logger = logging.getLogger(__name__)

async def get_redis_client():
    """Crée et retourne un client Redis."""
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    
    client = redis.Redis(
        host=redis_host,
        port=redis_port,
        decode_responses=True
    )
    return client

@pytest.mark.asyncio
async def test_user_queue_lifecycle(test_client, queue_manager_with_checker, test_logger):
    """Test le cycle de vie complet d'un utilisateur dans la file d'attente."""
    test_logger.info("Début du test du cycle de vie utilisateur")
    
    # Nettoyer Redis au début du test
    redis = await get_redis_client()
    await redis.flushdb()
    
    user_id = "test_lifecycle_user"
    
    # 1. Vérifier le statut initial
    test_logger.debug("Vérification du statut initial")
    response = await test_client.get(f"/queue/status/{user_id}")
    assert response.status_code == 200
    initial_status = response.json()
    assert initial_status["status"] is None
    
    # 2. Rejoindre la file d'attente
    test_logger.debug("Tentative de rejoindre la file d'attente")
    response = await test_client.post(f"/queue/join/{user_id}")
    assert response.status_code == 200
    join_result = response.json()
    test_logger.info(f"Statut après join: {join_result['commit_status']}")
    assert join_result["commit_status"] in ["waiting", "draft"]  # peut être draft directement si des slots sont disponibles
    assert join_result["commit_position"] is not None
    
    # 3. Vérifier le statut après avoir rejoint
    test_logger.debug("Vérification du statut après avoir rejoint")
    response = await test_client.get(f"/queue/status/{user_id}")
    assert response.status_code == 200
    current_status = response.json()
    test_logger.info(f"Statut actuel: {current_status['status']}")
    assert current_status["status"] in ["waiting", "draft"]  # peut être draft directement si des slots sont disponibles
    
    # Si l'utilisateur est en attente, attendre qu'un slot soit disponible
    if current_status["status"] == "waiting":
        test_logger.debug("Attente d'un slot disponible")
        max_wait = 30  # secondes
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < max_wait:
            response = await test_client.get(f"/queue/status/{user_id}")
            assert response.status_code == 200
            current_status = response.json()
            if current_status["status"] == "draft":
                test_logger.info("Slot obtenu, passage en draft")
                break
            await asyncio.sleep(1)
        assert current_status["status"] == "draft", "L'utilisateur n'a pas reçu de slot dans le temps imparti"
    
    # 4. Confirmer la connexion
    test_logger.debug("Confirmation de la connexion")
    response = await test_client.post(f"/queue/confirm/{user_id}")
    assert response.status_code == 200
    
    # 5. Vérifier le statut final
    test_logger.debug("Vérification du statut final")
    response = await test_client.get(f"/queue/status/{user_id}")
    assert response.status_code == 200
    final_status = response.json()
    assert final_status["status"] == "connected"
    
    test_logger.info("Fin du test du cycle de vie utilisateur")

@pytest.mark.asyncio
async def test_multiple_users_queue(test_client, queue_manager_with_checker, test_logger):
    """Test le comportement de la file d'attente avec plusieurs utilisateurs."""
    test_logger.info("Début du test multi-utilisateurs")
    
    # Nettoyer Redis au début du test
    redis = await get_redis_client()
    await redis.flushdb()
    
    # Créer plusieurs utilisateurs
    users = [f"test_user_{i}" for i in range(5)]
    user_statuses = {}
    
    # 1. Ajouter tous les utilisateurs à la file
    test_logger.debug("Ajout des utilisateurs à la file")
    draft_users = []
    waiting_users = []
    
    for user_id in users:
        response = await test_client.post(f"/queue/join/{user_id}")
        assert response.status_code == 200
        result = response.json()
        user_statuses[user_id] = {
            "initial_position": result["commit_position"],
            "status": result["commit_status"]
        }
        if result["commit_status"] == "draft":
            draft_users.append(user_id)
        else:
            waiting_users.append(user_id)
        test_logger.info(f"Utilisateur {user_id} ajouté avec statut {result['commit_status']}")
    
    test_logger.info(f"Utilisateurs en draft: {draft_users}")
    test_logger.info(f"Utilisateurs en attente: {waiting_users}")
    
    # Vérifier que les deux premiers utilisateurs sont en draft
    assert len(draft_users) == 2, f"Il devrait y avoir exactement 2 utilisateurs en draft, mais il y en a {len(draft_users)}"
    assert "test_user_0" in draft_users, "test_user_0 devrait être en draft"
    assert "test_user_1" in draft_users, "test_user_1 devrait être en draft"
    
    # Vérifier que les autres sont en attente
    assert len(waiting_users) == 3, f"Il devrait y avoir exactement 3 utilisateurs en attente, mais il y en a {len(waiting_users)}"
    for i in range(2, 5):
        assert f"test_user_{i}" in waiting_users, f"test_user_{i} devrait être en attente"
    
    # 2. Vérifier les métriques de la file
    test_logger.debug("Vérification des métriques")
    response = await test_client.get("/queue/metrics")
    assert response.status_code == 200
    metrics = response.json()
    test_logger.info(f"Métriques actuelles: {metrics}")
    
    # Vérifier que les métriques correspondent à l'état réel
    assert metrics["waiting_users"] == len(waiting_users), f"Le nombre d'utilisateurs en attente ne correspond pas (attendu: {len(waiting_users)}, reçu: {metrics['waiting_users']})"
    assert metrics["total_accounts"] == len(users), f"Le nombre total d'utilisateurs ne correspond pas (attendu: {len(users)}, reçu: {metrics['total_accounts']})"
    
    # 3. Confirmer la connexion pour les utilisateurs en draft
    test_logger.debug("Confirmation des connexions pour les utilisateurs en draft")
    for user_id in draft_users:
        test_logger.info(f"Confirmation de la connexion pour {user_id}")
        response = await test_client.post(f"/queue/confirm/{user_id}")
        assert response.status_code == 200
    
    # 4. Vérifier les métriques finales
    test_logger.debug("Vérification des métriques finales")
    response = await test_client.get("/queue/metrics")
    assert response.status_code == 200
    final_metrics = response.json()
    test_logger.info(f"Métriques finales: {final_metrics}")
    
    # Vérifier que les métriques finales correspondent à l'état attendu
    assert final_metrics["active_users"] == len(draft_users), f"Le nombre d'utilisateurs actifs ne correspond pas (attendu: {len(draft_users)}, reçu: {final_metrics['active_users']})"
    assert final_metrics["waiting_users"] == len(waiting_users), f"Le nombre d'utilisateurs en attente ne correspond pas (attendu: {len(waiting_users)}, reçu: {final_metrics['waiting_users']})"
    assert final_metrics["total_accounts"] == len(users), f"Le nombre total d'utilisateurs ne correspond pas (attendu: {len(users)}, reçu: {final_metrics['total_accounts']})"
    
    test_logger.info("Fin du test multi-utilisateurs") 

@pytest.mark.asyncio
async def test_check_available_slots():
    """Test la vérification des slots disponibles."""
    logger.info("Début du test de check_available_slots")
    
    # Initialisation
    redis = await get_redis_client()
    queue_manager = QueueManager(redis)
    
    try:
        # Nettoyer Redis au début du test
        await redis.flushdb()
        
        # Vérifier les slots disponibles initialement
        slots_available = await queue_manager.check_available_slots()
        assert slots_available == True, "Des slots devraient être disponibles au départ"
        
        # Ajouter des utilisateurs actifs jusqu'à la limite
        async with redis.pipeline(transaction=True) as pipe:
            for i in range(queue_manager.max_active_users):
                user_id = f"active_user_{i}"
                pipe.sadd('active_users', user_id)
            await pipe.execute()
            
        # Vérifier qu'il n'y a plus de slots disponibles
        slots_available = await queue_manager.check_available_slots()
        assert slots_available == False, "Aucun slot ne devrait être disponible"
        
        # Ajouter des utilisateurs en attente
        waiting_users = []
        async with redis.pipeline(transaction=True) as pipe:
            for i in range(3):
                user_id = f"waiting_user_{i}"
                waiting_users.append(user_id)
                pipe.rpush('waiting_queue', user_id)
                pipe.sadd('queued_users', user_id)
            await pipe.execute()
            
        # Vérifier que les slots ne sont pas offerts quand il n'y en a pas
        slots_available = await queue_manager.check_available_slots()
        assert slots_available == False, "Aucun slot ne devrait être disponible"
        
        # Libérer un slot
        await redis.srem('active_users', 'active_user_0')
        
        # Vérifier que les slots sont maintenant disponibles
        slots_available = await queue_manager.check_available_slots()
        assert slots_available == False, "Le slot libéré a été pris par un utilisateur en draft"
        
        # Vérifier qu'un utilisateur est passé en draft
        is_draft = await redis.sismember('draft_users', 'waiting_user_0')
        assert is_draft == True, "Le premier utilisateur en attente devrait être passé en draft"
        
    finally:
        # Nettoyage
        await redis.flushdb()
        await redis.aclose()
        logger.info("Fin du test de check_available_slots")

@pytest.mark.asyncio
async def test_offer_slot():
    """Test l'offre d'un slot à un utilisateur."""
    logger.info("Début du test de offer_slot")
    
    # Initialisation
    redis = await get_redis_client()
    queue_manager = QueueManager(redis)
    
    try:
        # Ajouter un utilisateur en attente
        user_id = "test_user"
        async with redis.pipeline(transaction=True) as pipe:
            pipe.rpush('waiting_queue', user_id)
            pipe.sadd('queued_users', user_id)
            await pipe.execute()
            
        # Vérifier l'état initial
        position = await redis.lpos('waiting_queue', user_id)
        assert position is not None, "L'utilisateur devrait être dans la waiting_queue"
        is_queued = await redis.sismember('queued_users', user_id)
        assert is_queued == True, "L'utilisateur devrait être dans queued_users"
        
        # Offrir un slot
        slot_offered = await queue_manager.offer_slot(user_id)
        assert slot_offered == True, "Le slot devrait être offert avec succès"
        
        # Vérifier l'état après l'offre
        position = await redis.lpos('waiting_queue', user_id)
        assert position is None, "L'utilisateur ne devrait plus être dans la waiting_queue"
        is_queued = await redis.sismember('queued_users', user_id)
        assert is_queued == False, "L'utilisateur ne devrait plus être dans queued_users"
        is_draft = await redis.sismember('draft_users', user_id)
        assert is_draft == True, "L'utilisateur devrait être dans draft_users"
        has_draft_key = await redis.exists(f'draft:{user_id}')
        assert has_draft_key == True, "L'utilisateur devrait avoir une clé draft"
        
        # Tester l'offre à un utilisateur non éligible
        slot_offered = await queue_manager.offer_slot("non_existent_user")
        assert slot_offered == False, "Le slot ne devrait pas être offert à un utilisateur non éligible"
        
    finally:
        # Nettoyage
        await redis.flushdb()
        await redis.aclose()
        logger.info("Fin du test de offer_slot") 