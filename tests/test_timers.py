import pytest
from httpx import AsyncClient
from app.main import app
from app.queue_manager import QueueManager, update_timer_channel
import asyncio
import os
import json
import celery

@pytest.fixture
def queue_manager(redis_client):
    return QueueManager(redis_client)

class TestTimers:
    @pytest.mark.asyncio
    async def test_draft_timer_redis(self, queue_manager, redis_client):
        user_id = "test_user_draft"
        
        # Ajouter l'utilisateur à la file d'attente d'abord
        await queue_manager.add_to_queue(user_id)
        
        # Offrir un slot
        await queue_manager.offer_slot(user_id)
        exists = await redis_client.exists(f"draft:{user_id}")
        assert exists
        
        # Vérifier le TTL avant le nettoyage
        ttl = await redis_client.ttl(f"draft:{user_id}")
        assert 0 < ttl <= queue_manager.draft_duration
        
        # Nettoyage
        await redis_client.delete(f"draft:{user_id}")
        await redis_client.srem("draft_users", user_id)
        await redis_client.srem("queued_users", user_id)
        await redis_client.lrem("waiting_queue", 0, user_id)
        
        await asyncio.sleep(2)
        
        new_ttl = await redis_client.ttl(f"draft:{user_id}")
        assert new_ttl < ttl

    @pytest.mark.asyncio
    async def test_session_timer_redis(self, queue_manager, redis_client):
        user_id = "test_user_session"
        
        # Setup: ajouter l'utilisateur en draft d'abord
        await redis_client.sadd("draft_users", user_id)
        await redis_client.setex(f"draft:{user_id}", queue_manager.draft_duration, "1")
        
        # Confirmer la connexion
        success = await queue_manager.confirm_connection(user_id)
        assert success, "La confirmation de connexion a échoué"
        
        exists = await redis_client.exists(f"session:{user_id}")
        assert exists, "La session n'existe pas"
        
        ttl = await redis_client.ttl(f"session:{user_id}")
        assert 0 < ttl <= queue_manager.session_duration
        
        # Vérifier que l'utilisateur est bien en session
        is_active = await redis_client.sismember("active_users", user_id)
        assert is_active, "L'utilisateur n'est pas actif"

    @pytest.mark.asyncio
    async def test_get_timers_endpoint_draft(self, test_client, redis_client, test_logger, celery_app):
        """Test la récupération des timers pour un utilisateur en draft."""
        user_id = "test_user_api_draft"
        
        # Configuration de Celery pour le test
        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
            broker_url='redis://localhost:6379/0',
            result_backend='redis://localhost:6379/0',
            broker_connection_retry_on_startup=True
        )
        
        # Créer un draft
        await redis_client.setex(f"draft:{user_id}", 300, "1")
        await redis_client.sadd("draft_users", user_id)
        
        try:
            # Récupérer les timers
            response = await test_client.get(f"/queue/timers/{user_id}")
            assert response.status_code == 200
            timers = response.json()
            test_logger.info(f"Timers reçus: {timers}")
            
            # Vérifier le contenu
            assert timers["timer_type"] == "draft", "Type de timer incorrect"
            assert timers["ttl"] > 0, "TTL invalide"
            assert "channel" in timers, "Channel manquant"
            assert timers["channel"] == f"timer:channel:{user_id}", "Channel incorrect"
            
            # Vérifier que la tâche a été créée
            task_id = timers.get("task_id")
            assert task_id is not None, "Task ID manquant"
            assert isinstance(task_id, str), "Task ID devrait être une chaîne"
            assert len(task_id) > 0, "Task ID ne devrait pas être vide"
            
        finally:
            # Cleanup
            await redis_client.delete(f"draft:{user_id}")
            await redis_client.srem("draft_users", user_id)

    @pytest.mark.asyncio
    async def test_get_timers_endpoint_session(self, test_client, redis_client, test_logger, celery_app):
        """Test la récupération des timers pour un utilisateur en session."""
        user_id = "test_user_api_session"
        
        # Configuration de Celery pour le test
        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
            broker_url='redis://localhost:6379/0',
            result_backend='redis://localhost:6379/0',
            broker_connection_retry_on_startup=True
        )
        
        # Créer une session active
        await redis_client.setex(f"session:{user_id}", 1200, "1")
        await redis_client.sadd("active_users", user_id)
        
        try:
            # Récupérer les timers
            response = await test_client.get(f"/queue/timers/{user_id}")
            assert response.status_code == 200
            timers = response.json()
            test_logger.info(f"Timers reçus: {timers}")
            
            # Vérifier le contenu
            assert timers["timer_type"] == "session", "Type de timer incorrect"
            assert timers["ttl"] > 0, "TTL invalide"
            assert "channel" in timers, "Channel manquant"
            assert timers["channel"] == f"timer:channel:{user_id}", "Channel incorrect"
            
            # Vérifier que la tâche a été créée
            task_id = timers.get("task_id")
            assert task_id is not None, "Task ID manquant"
            assert isinstance(task_id, str), "Task ID devrait être une chaîne"
            assert len(task_id) > 0, "Task ID ne devrait pas être vide"
            
        finally:
            # Cleanup
            await redis_client.delete(f"session:{user_id}")
            await redis_client.srem("active_users", user_id)

    @pytest.mark.asyncio
    async def test_get_timers_endpoint_both(self, test_client, redis_client):
        user_id = "test_user_api_session"
        user_id_draft = "test_user_api_draft"
        await redis_client.sadd("draft_users", user_id_draft)
        await redis_client.sadd("active_users", user_id)
        len_draft_users = await redis_client.scard("draft_users")
        len_active_users = await redis_client.scard("active_users")
        assert len_draft_users == 1, f"len_draft_users is {len_draft_users}"
        assert len_active_users == 1, f"len_active_users is {len_active_users}"
        await redis_client.setex(f"draft:{user_id_draft}", 300, "1")
        await redis_client.setex(f"session:{user_id}", 1200, "1")
        
        response = await test_client.get(f"/queue/timers/{user_id}")
        response_draft = await test_client.get(f"/queue/timers/{user_id_draft}")
        assert response.status_code == 200
        
        timers = response.json()
        timers_draft = response_draft.json()

        # Le draft a priorité sur la session
        assert timers_draft["timer_type"] == "draft" , f"timer_type is {timers_draft}"
        assert 0 < timers_draft["ttl"] <= 300 , f"ttl is {timers_draft['ttl']}"
        
        await redis_client.delete(f"draft:{user_id_draft}")
        await redis_client.delete(f"session:{user_id}")
        await redis_client.srem("draft_users", user_id_draft)
        await redis_client.srem("active_users", user_id)
        len_draft_users = await redis_client.scard("draft_users")
        len_active_users = await redis_client.scard("active_users")
        assert len_draft_users == 0, f"len_draft_users is {len_draft_users}"
        assert len_active_users == 0, f"len_active_users is {len_active_users}"

    @pytest.mark.asyncio
    async def test_get_timers_endpoint_no_timers(self, test_client, redis_client):
        """Test la récupération des timers pour un utilisateur sans timer actif."""
        user_id = "test_user_api_none"
        response = await test_client.get(f"/queue/timers/{user_id}")
        assert response.status_code == 200
        timers = response.json()
        assert "error" in timers, f"La réponse devrait être un objet vide, reçu: {timers}"

    @pytest.mark.asyncio
    async def test_pubsub_connection_draft(self, queue_manager_with_checker, test_client, test_logger, redis_client, celery_app):
        """Test la connexion pubsub pour le draft."""
        test_logger.info("Démarrage du test pubsub draft")
        user_id = "test_user_pubsub_draft"

        try:
            # Ajouter l'utilisateur à la file
            test_logger.debug(f"Ajout de l'utilisateur {user_id} à la file")
            response = await test_client.post(f"/queue/join/{user_id}")
            assert response.status_code == 200

            # Attendre que l'utilisateur soit en draft
            test_logger.debug("Attente du placement en draft")
            max_wait = 2  # 2 secondes maximum
            start_time = asyncio.get_event_loop().time()
            is_draft = False

            while not is_draft and (asyncio.get_event_loop().time() - start_time) < max_wait:
                is_draft = await redis_client.sismember('draft_users', user_id)
                if not is_draft:
                    await asyncio.sleep(0.1)

            assert is_draft, "L'utilisateur n'a pas été placé en draft après 2 secondes"
            test_logger.info("Utilisateur placé en draft avec succès")

            # S'abonner au canal PubSub avant d'activer les timers
            pubsub = redis_client.pubsub()
            channel = f"timer:channel:{user_id}"
            await pubsub.subscribe(channel)
            test_logger.info(f"Abonnement au canal {channel}")

            # Vérifier le TTL du draft
            draft_ttl = await redis_client.ttl(f"draft:{user_id}")
            test_logger.info(f"TTL initial du draft: {draft_ttl}")
            assert draft_ttl > 0, "Le TTL du draft devrait être positif"

            # Simuler les mises à jour du timer
            from test_timers_async import execute_timer_task
            messages = []
            current_ttl = draft_ttl

            # Simuler 3 mises à jour avec diminution du TTL
            for i in range(3):
                test_logger.info(f"Exécution {i+1} avec TTL={current_ttl}")
                
                # Mettre à jour le TTL dans Redis
                await redis_client.setex(f"draft:{user_id}", current_ttl, "1")
                
                # Lancer la tâche
                task = await execute_timer_task(
                    channel=channel,
                    initial_ttl=current_ttl,
                    timer_type="draft",
                    max_updates=1,
                    test_logger=test_logger
                )
                
                # Attendre et collecter le message
                message = None
                start_time = asyncio.get_event_loop().time()
                while (asyncio.get_event_loop().time() - start_time) < 3:  # 3 secondes max par message
                    msg = await pubsub.get_message(timeout=1.0)
                    if msg and msg['type'] == 'message':
                        message = json.loads(msg['data'])
                        test_logger.info(f"Message reçu: {message}")
                        break
                    await asyncio.sleep(0.1)
                
                assert message is not None, f"Pas de message reçu pour l'itération {i+1}"
                messages.append(message)
                
                # Diminuer le TTL pour la prochaine itération
                current_ttl = max(1, current_ttl - 2)
                await asyncio.sleep(0.5)  # Attendre un peu entre les messages

            # Vérifier les messages
            assert len(messages) == 3, f"Attendu 3 messages, reçu {len(messages)}"
            
            # Vérifier que les TTL sont décroissants
            ttls = [msg['ttl'] for msg in messages]
            test_logger.info(f"TTLs reçus: {ttls}")
            assert all(ttls[i] > ttls[i+1] for i in range(len(ttls)-1)), "Les TTL devraient être décroissants"

        except Exception as e:
            test_logger.error(f"Erreur pendant le test: {str(e)}")
            raise
        finally:
            # Cleanup
            if pubsub:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            await redis_client.delete(f"draft:{user_id}")
            await redis_client.srem("draft_users", user_id)
            await redis_client.delete(f"status_history:{user_id}")
            await redis_client.delete(f"last_status:{user_id}")
            test_logger.info("Nettoyage terminé")

    @pytest.mark.asyncio
    async def test_pubsub_connection_session(self, test_client, redis_client, queue_manager_with_checker, test_logger, celery_app):
        """Test la connexion PubSub pour les timers de session."""
        user_id = "test_user_pubsub_session"
        messages = []
        pubsub = None
        channel = None
        
        try:
            # Ajouter l'utilisateur à la file d'attente
            test_logger.debug(f"Ajout de l'utilisateur {user_id} à la file")
            join_response = await test_client.post(f"/queue/join/{user_id}")
            assert join_response.status_code == 200
            test_logger.info("Utilisateur ajouté à la file d'attente")
            
            # Attendre que le slot checker place l'utilisateur en draft
            test_logger.debug("Attente du placement en draft")
            max_wait = 2  # 2 secondes maximum
            start_time = asyncio.get_event_loop().time()
            is_draft = False
            
            while not is_draft and (asyncio.get_event_loop().time() - start_time) < max_wait:
                is_draft = await redis_client.sismember('draft_users', user_id)
                if not is_draft:
                    await asyncio.sleep(0.1)
            
            assert is_draft, "L'utilisateur n'a pas été placé en draft après 2 secondes"
            test_logger.info(f"Utilisateur {user_id} placé en draft avec succès")
            
            # Confirmer la connexion
            test_logger.debug("Tentative de confirmation de la connexion")
            confirm_response = await test_client.post(f"/queue/confirm/{user_id}")
            assert confirm_response.status_code == 200
            test_logger.info(f"Connexion de l'utilisateur {user_id} confirmée avec succès")
            
            # Vérifier que l'utilisateur n'est plus dans draft et est maintenant dans active_users
            test_logger.debug("Vérification de l'état de l'utilisateur")
            is_draft = await redis_client.sismember('draft_users', user_id)
            assert not is_draft, "L'utilisateur ne devrait plus être dans draft après la confirmation"
            is_active = await redis_client.sismember('active_users', user_id)
            assert is_active, "L'utilisateur devrait être dans active_users après la confirmation"

            # Setup pubsub connection
            test_logger.debug("Configuration de la connexion PubSub")
            pubsub = redis_client.pubsub()
            channel = f"timer:channel:{user_id}"
            await pubsub.subscribe(channel)
            test_logger.info(f"Abonnement PubSub réussi pour le channel {channel}")

            # Vérifier le TTL de la session
            session_ttl = await redis_client.ttl(f"session:{user_id}")
            assert session_ttl > 0, "Le TTL de la session devrait être positif"
            test_logger.info(f"TTL de la session: {session_ttl}")

            # Simuler les mises à jour du timer
            from test_timers_async import execute_timer_task
            messages = []
            current_ttl = session_ttl

            # Simuler 3 mises à jour avec diminution du TTL
            for i in range(3):
                test_logger.info(f"Exécution {i+1} avec TTL={current_ttl}")
                
                # Mettre à jour le TTL dans Redis
                await redis_client.setex(f"session:{user_id}", current_ttl, "1")
                
                # Lancer la tâche
                task = await execute_timer_task(
                    channel=channel,
                    initial_ttl=current_ttl,
                    timer_type="session",
                    max_updates=1,
                    test_logger=test_logger
                )
                
                # Attendre et collecter le message
                message = None
                start_time = asyncio.get_event_loop().time()
                while (asyncio.get_event_loop().time() - start_time) < 3:  # 3 secondes max par message
                    msg = await pubsub.get_message(timeout=1.0)
                    if msg and msg['type'] == 'message':
                        message = json.loads(msg['data'])
                        test_logger.info(f"Message reçu: {message}")
                        break
                    await asyncio.sleep(0.1)
                
                assert message is not None, f"Pas de message reçu pour l'itération {i+1}"
                messages.append(message)
                
                # Diminuer le TTL pour la prochaine itération
                current_ttl = max(1, current_ttl - 2)
                await asyncio.sleep(0.5)  # Attendre un peu entre les messages

            # Vérifier les messages
            assert len(messages) == 3, f"Attendu 3 messages, reçu {len(messages)}"
            
            # Vérifier que les TTL sont décroissants
            ttls = [msg['ttl'] for msg in messages]
            test_logger.info(f"TTLs reçus: {ttls}")
            assert all(ttls[i] > ttls[i+1] for i in range(len(ttls)-1)), "Les TTL devraient être décroissants"

        except Exception as e:
            test_logger.error(f"Erreur pendant le test: {str(e)}")
            raise
        finally:
            # Cleanup
            if pubsub:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            await redis_client.delete(f"session:{user_id}")
            await redis_client.srem("active_users", user_id)
            await redis_client.delete(f"status_history:{user_id}")
            await redis_client.delete(f"last_status:{user_id}")
            test_logger.info("Nettoyage terminé")

    @pytest.mark.asyncio
    async def test_pubsub_multiple_updates(self, test_client, redis_client, queue_manager_with_checker, test_logger):
        """Test la réception de plusieurs mises à jour de timer en mode asynchrone."""
        from celery_test_config import setup_test_celery
        from app.queue_manager import update_timer_channel

        # Configuration de Celery en mode asynchrone
        celery_app = setup_test_celery()
        test_logger.info("Celery configuré en mode asynchrone")

        user_id = "test_user_pubsub_multiple"
        messages = []
        pubsub = None
        channel = None

        try:
            # Ajouter l'utilisateur à la file d'attente
            test_logger.debug(f"Ajout de l'utilisateur {user_id} à la file")
            join_response = await test_client.post(f"/queue/join/{user_id}")
            assert join_response.status_code == 200
            test_logger.info("Utilisateur ajouté à la file d'attente")
            
            # Attendre que le slot checker place l'utilisateur en draft
            test_logger.debug("Attente du placement en draft")
            max_wait = 2  # 2 secondes maximum
            start_time = asyncio.get_event_loop().time()
            is_draft = False
            
            while not is_draft and (asyncio.get_event_loop().time() - start_time) < max_wait:
                is_draft = await redis_client.sismember('draft_users', user_id)
                if not is_draft:
                    await asyncio.sleep(0.1)
            
            assert is_draft, "L'utilisateur n'a pas été placé en draft après 2 secondes"
            test_logger.info(f"Utilisateur {user_id} placé en draft avec succès")

            # Setup pubsub connection
            test_logger.debug("Configuration de la connexion PubSub")
            pubsub = redis_client.pubsub()
            channel = f"timer:channel:{user_id}"
            await pubsub.subscribe(channel)
            test_logger.info(f"Abonnement PubSub réussi pour le channel {channel}")

            # Vérifier le TTL du draft
            draft_ttl = await redis_client.ttl(f"draft:{user_id}")
            assert draft_ttl > 0, "Le TTL du draft devrait être positif"
            test_logger.info(f"TTL du draft: {draft_ttl}")

            # Lancer la tâche de manière asynchrone
            test_logger.debug("Lancement de la tâche update_timer_channel en mode asynchrone")
            from test_timers_async import execute_timer_task
            
            # Initialiser les variables pour le suivi des messages
            messages = []
            current_ttl = draft_ttl
            
            # Simuler 3 mises à jour avec diminution du TTL
            for i in range(3):
                test_logger.info(f"Exécution {i+1} avec TTL={current_ttl}")
                
                # Mettre à jour le TTL dans Redis
                await redis_client.setex(f"draft:{user_id}", current_ttl, "1")
                
                # Lancer la tâche
                task = await execute_timer_task(
                    channel=channel,
                    initial_ttl=current_ttl,
                    timer_type="draft",
                    max_updates=1,
                    test_logger=test_logger
                )
                
                # Attendre et collecter le message
                message = None
                start_time = asyncio.get_event_loop().time()
                while (asyncio.get_event_loop().time() - start_time) < 3:  # 3 secondes max par message
                    msg = await pubsub.get_message(timeout=1.0)
                    if msg and msg['type'] == 'message':
                        message = json.loads(msg['data'])
                        test_logger.info(f"Message reçu: {message}")
                        break
                    await asyncio.sleep(0.1)
                
                assert message is not None, f"Pas de message reçu pour l'itération {i+1}"
                messages.append(message)
                
                # Diminuer le TTL pour la prochaine itération
                current_ttl = max(1, current_ttl - 2)
                await asyncio.sleep(0.5)  # Attendre un peu entre les messages

            # Vérifier les messages
            assert len(messages) == 3, f"Attendu 3 messages, reçu {len(messages)}"
            
            # Vérifier que les TTL sont décroissants
            ttls = [msg['ttl'] for msg in messages]
            test_logger.info(f"TTLs reçus: {ttls}")
            assert all(ttls[i] > ttls[i+1] for i in range(len(ttls)-1)), "Les TTL devraient être décroissants"

        except Exception as e:
            test_logger.error(f"Erreur pendant le test: {str(e)}")
            raise
        finally:
            # Cleanup
            if pubsub:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            await redis_client.delete(f"draft:{user_id}")
            await redis_client.srem("draft_users", user_id)
            await redis_client.delete(f"status_history:{user_id}")
            await redis_client.delete(f"last_status:{user_id}")
            test_logger.info("Nettoyage terminé")

@pytest.mark.asyncio
async def test_update_timer_channel_expiration(celery_app, redis_client, test_logger):
    """Test de l'expiration du timer."""
    test_logger.info("Démarrage du test d'expiration du timer")

    # Configuration de Celery
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        task_store_eager_result=True,
        result_backend='cache',
        cache_backend='memory'
    )

    # Enregistrer la tâche dans Celery
    from app.queue_manager import update_timer_channel
    celery_app.tasks.register(update_timer_channel)

    # Créer une clé de draft avec un TTL court
    user_id = "test_timer_expiration"
    channel = f"timer:channel:{user_id}"
    ttl = 2  # TTL de 2 secondes

    # Créer la clé de draft et ajouter l'utilisateur au set draft_users
    await redis_client.setex(f"draft:{user_id}", ttl, "1")
    await redis_client.sadd("draft_users", user_id)
    test_logger.info(f"Clé de draft créée: draft:{user_id} avec TTL={ttl}")

    # S'abonner au canal
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    test_logger.info(f"Abonnement au canal {channel}")

    try:
        # Vérifier le TTL initial
        initial_ttl = await redis_client.ttl(f"draft:{user_id}")
        test_logger.info(f"TTL initial: {initial_ttl}")
        assert initial_ttl > 0, "Le TTL initial devrait être positif"

        # Attendre que le TTL diminue
        await asyncio.sleep(1)
        
        # Vérifier que le TTL a diminué
        current_ttl = await redis_client.ttl(f"draft:{user_id}")
        test_logger.info(f"TTL après 1 seconde: {current_ttl}")
        assert current_ttl < initial_ttl, "Le TTL devrait avoir diminué"

        # Attendre l'expiration complète
        await asyncio.sleep(ttl)
        
        # Vérifier que la clé a expiré
        exists = await redis_client.exists(f"draft:{user_id}")
        test_logger.info(f"Existence de la clé après expiration: {exists}")
        assert not exists, "La clé devrait avoir expiré"

        # Déclencher le nettoyage du draft
        from app.queue_manager import handle_draft_expiration
        await handle_draft_expiration(user_id)
        test_logger.info("Nettoyage du draft déclenché")

        # Vérifier que l'utilisateur n'est plus dans draft_users
        is_draft = await redis_client.sismember("draft_users", user_id)
        test_logger.info(f"Utilisateur toujours en draft: {is_draft}")
        assert not is_draft, "L'utilisateur ne devrait plus être en draft"

    finally:
        # Nettoyage
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await redis_client.delete(f"draft:{user_id}")
        await redis_client.srem("draft_users", user_id)
        test_logger.info("Test terminé, nettoyage effectué")

@pytest.mark.asyncio
async def test_update_timer_channel(celery_app, redis_client, test_logger):
    """Test de la tâche update_timer_channel."""
    test_logger.info("Démarrage du test de update_timer_channel")
    
    # Configuration de Celery
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        task_store_eager_result=True,
        result_backend='cache',
        cache_backend='memory'
    )
    
    # Enregistrer la tâche dans Celery
    from app.queue_manager import update_timer_channel
    celery_app.tasks.register(update_timer_channel)
    
    # Créer une clé de session avec un TTL
    user_id = "test_timer_user"
    channel = f"timer:channel:{user_id}"
    ttl = 5
    
    # Créer la clé de session et ajouter l'utilisateur au set active_users
    await redis_client.setex(f"session:{user_id}", ttl, "1")
    await redis_client.sadd("active_users", user_id)
    test_logger.info(f"Clé de session créée: session:{user_id} avec TTL={ttl}")
    
    # S'abonner au canal
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    test_logger.info(f"Abonnement au canal {channel}")
    
    try:
        # Lancer la tâche de manière asynchrone
        test_logger.debug("Lancement de la tâche update_timer_channel en mode asynchrone")
        from test_timers_async import execute_timer_task
        
        # Initialiser les variables pour le suivi des messages
        messages = []
        current_ttl = ttl
        
        # Simuler 3 mises à jour avec diminution du TTL
        for i in range(3):
            test_logger.info(f"Exécution {i+1} avec TTL={current_ttl}")
            
            # Mettre à jour le TTL dans Redis
            await redis_client.setex(f"session:{user_id}", current_ttl, "1")
            
            # Lancer la tâche
            task = await execute_timer_task(
                channel=channel,
                initial_ttl=current_ttl,
                timer_type="session",
                max_updates=1,
                test_logger=test_logger
            )
            
            # Attendre et collecter le message
            message = None
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < 3:  # 3 secondes max par message
                msg = await pubsub.get_message(timeout=1.0)
                if msg and msg['type'] == 'message':
                    message = json.loads(msg['data'])
                    test_logger.info(f"Message reçu: {message}")
                    break
                await asyncio.sleep(0.1)
            
            assert message is not None, f"Pas de message reçu pour l'itération {i+1}"
            messages.append(message)
            
            # Diminuer le TTL pour la prochaine itération
            current_ttl = max(1, current_ttl - 2)
            await asyncio.sleep(0.5)  # Attendre un peu entre les messages

        # Vérifier les messages
        assert len(messages) == 3, f"Attendu 3 messages, reçu {len(messages)}"
        
        # Vérifier que les TTL sont décroissants
        ttls = [msg['ttl'] for msg in messages]
        test_logger.info(f"TTLs reçus: {ttls}")
        assert all(ttls[i] > ttls[i+1] for i in range(len(ttls)-1)), "Les TTL devraient être décroissants"

    except Exception as e:
        test_logger.error(f"Erreur lors de l'exécution de update_timer_channel: {str(e)}")
        raise
    finally:
        # Cleanup
        test_logger.debug("Nettoyage")
        if pubsub:  # Vérifier si pubsub a été créé
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        await redis_client.delete(f"session:{user_id}")
        await redis_client.srem("active_users", user_id)
        test_logger.info("Test terminé, nettoyage effectué") 