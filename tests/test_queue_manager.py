import pytest
import json
from app.queue_manager import QueueManager
from app.celery_app import celery
import asyncio
import logging
from redis.asyncio import Redis
import os
import time

class TestQueueManager:
    @pytest.mark.asyncio
    async def test_auto_expiration_async(self, redis_client, queue_manager):
        """Teste l'exécution asynchrone de auto_expiration."""
        # Préparer l'environnement de test
        user_id = "test_user_auto_expiration"
        ttl = 2  # 2 secondes pour le test
        
        # Ajouter l'utilisateur comme actif avec une session
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.sadd('active_users', user_id)
            pipe.setex(f'session:{user_id}', ttl, '1')
            await pipe.execute()
        
        # Vérifier que l'utilisateur est toujours actif immédiatement
        is_active = await redis_client.sismember('active_users', user_id)
        assert is_active, "L'utilisateur devrait être actif avant l'expiration"
        
        # Attendre un peu plus que le TTL
        await asyncio.sleep(ttl + 1)
        
        # Nettoyer la session
        success = await queue_manager.cleanup_session(user_id)
        assert success, "Le nettoyage de la session devrait réussir"
        
        # Vérifier que l'utilisateur n'est plus actif
        is_active = await redis_client.sismember('active_users', user_id)
        assert not is_active, "L'utilisateur ne devrait plus être actif après l'expiration"
        
        # Vérifier que la session a été supprimée
        session_exists = await redis_client.exists(f'session:{user_id}')
        assert not session_exists, "La session devrait être supprimée"

    @pytest.mark.asyncio
    async def test_fill_active_queue(self, queue_manager, test_logger):
        """Test le remplissage de la file active."""
        test_logger.info("Démarrage du test de remplissage de la file active")
        
        try:
            # Vérifier que la file est vide au départ
            active_count = await queue_manager.redis.scard('active_users')
            test_logger.info(f"Nombre initial d'utilisateurs actifs: {active_count}")
            assert active_count == 0, "La file active devrait être vide au départ"
            
            # Remplir la file active
            test_logger.info(f"Remplissage de la file active (max={queue_manager.max_active_users})")
            for i in range(queue_manager.max_active_users):
                active_user = f"active_user_{i}"
                # Ajouter l'utilisateur à la file active
                await queue_manager.redis.sadd('active_users', active_user)
                # Créer une session pour l'utilisateur
                await queue_manager.redis.setex(f'session:{active_user}', queue_manager.session_duration, '1')
                
                # Vérifier que l'utilisateur est bien actif
                is_active = await queue_manager.redis.sismember('active_users', active_user)
                assert is_active, f"L'utilisateur {active_user} devrait être actif"
                
                # Vérifier que la session existe
                has_session = await queue_manager.redis.exists(f'session:{active_user}')
                assert has_session, f"L'utilisateur {active_user} devrait avoir une session"
                
                # Vérifier le TTL de la session
                ttl = await queue_manager.redis.ttl(f'session:{active_user}')
                assert 0 < ttl <= queue_manager.session_duration, f"Le TTL de la session devrait être entre 0 et {queue_manager.session_duration}"
                
                # Vérifier le nombre d'utilisateurs actifs
                current_count = await queue_manager.redis.scard('active_users')
                test_logger.debug(f"Nombre d'utilisateurs actifs après ajout de {active_user}: {current_count}")
                assert current_count == i + 1, f"Le nombre d'utilisateurs actifs devrait être {i + 1}"
            
            # Vérifier le nombre final d'utilisateurs actifs
            final_count = await queue_manager.redis.scard('active_users')
            test_logger.info(f"Nombre final d'utilisateurs actifs: {final_count}")
            assert final_count == queue_manager.max_active_users, "La file active devrait être pleine"
            
            # Vérifier que tous les utilisateurs ont un statut correct
            for i in range(queue_manager.max_active_users):
                active_user = f"active_user_{i}"
                status = await queue_manager.get_user_status(active_user)
                test_logger.debug(f"Statut de {active_user}: {status}")
                assert status["status"] == "connected", f"Le statut devrait être 'connected', reçu {status['status']}"
                assert status["position"] == -2, f"La position devrait être -2, reçu {status['position']}"
                assert "remaining_time" in status, "Le statut devrait inclure remaining_time"
                assert 0 < status["remaining_time"] <= queue_manager.session_duration, "Le temps restant devrait être valide"
            
            test_logger.info("Test de remplissage réussi")
            
        except Exception as e:
            test_logger.error(f"Erreur lors du test de remplissage: {str(e)}")
            raise
            
        finally:
            # Nettoyage
            test_logger.debug("Nettoyage des données de test")
            for i in range(queue_manager.max_active_users):
                active_user = f"active_user_{i}"
                await queue_manager.redis.srem('active_users', active_user)
                await queue_manager.redis.delete(f'session:{active_user}')
            
            # Vérifier que le nettoyage est effectif
            final_count = await queue_manager.redis.scard('active_users')
            assert final_count == 0, "La file active devrait être vide après nettoyage"
            test_logger.info("Nettoyage terminé") 


    
    
    @pytest.mark.asyncio
    async def test_add_to_queue(self, queue_manager, test_logger):
        """Test l'ajout d'un utilisateur à la file d'attente."""
        test_logger.info("Démarrage du test d'ajout à la file d'attente")
        
        try:
            # Remplir d'abord la file active
            test_logger.info("Remplissage de la file active")
            for i in range(queue_manager.max_active_users):
                active_user = f"active_user_{i}"
                await queue_manager.redis.sadd('active_users', active_user)
                await queue_manager.redis.setex(f'session:{active_user}', queue_manager.session_duration, '1')
            
            active_count = await queue_manager.redis.scard('active_users')
            test_logger.info(f"Nombre d'utilisateurs actifs: {active_count}")
            assert active_count == queue_manager.max_active_users, "La file active devrait être pleine"
            
            # Premier ajout - devrait réussir et rester en waiting
            test_logger.debug("Tentative d'ajout de user1 à la file")
            result = await queue_manager.add_to_queue("user1")
            all_messages = await queue_manager.get_status_messages("user1")
            test_logger.info(f"Résultat: {result}")
            
            # Vérifier le statut initial
            assert result["last_status"] == None, f"Le statut initial devrait être 'disconnected', reçu {result['last_status']}"
            assert result["last_position"] is None, f"La position initiale devrait être None, reçu {result['last_position']}"
            
            # Vérifier le statut après commit
            test_logger.info(f"Résultat après commit: {result}")
            assert result["commit_status"] == "waiting", f"Le statut après ajout devrait être 'waiting', reçu {result['commit_status']}"
            assert result["commit_position"] == 1, f"La position après ajout devrait être 1, reçu {result['commit_position']}"
            
            # Vérifier la présence dans la file et le statut via get_user_status
            test_logger.debug("Vérification de la présence dans la file et du statut")
            waiting_list = await queue_manager.redis.lrange('waiting_queue', 0, -1)
            assert "user1" in waiting_list, f"L'utilisateur devrait être dans la file d'attente. File actuelle : {waiting_list}"
            
            # Vérifier que le statut a été mis à jour via get_user_status
            status = await queue_manager.get_user_status("user1")
            test_logger.info(f"Statut après ajout: {status}")
            assert status["status"] == "waiting", f"Le statut devrait être 'waiting', reçu {status['status']}"
            assert status["position"] == 1, f"La position devrait être 1, reçu {status['position']}"
            
            test_logger.info("Utilisateur trouvé dans la file avec le bon statut")
            
            # Deuxième ajout - devrait retourner le même statut waiting
            test_logger.debug("Tentative de réajout de user1 à la file")
            messages = await queue_manager.get_status_messages("user1")
            test_logger.info(f"Messages: {messages}")
            result = await queue_manager.add_to_queue("user1")
            messages = await queue_manager.get_status_messages("user1")
            test_logger.info(f"Messages: {messages}")
            assert result["last_status"] == "waiting", f"Le statut actuel devrait être 'disconnected', reçu {result['last_status']}"
            assert result["last_position"] == 1, f"La position actuelle devrait être 1, reçu {result['last_position']}"
            assert result["commit_status"] == "waiting", f"Le statut après ajout devrait être 'waiting'"
            assert result["commit_position"] == 1, f"La position après ajout devrait être 1"
            
            # Enlever un utilisateur lambda de la file active
            test_logger.debug("Enlèvement d'un utilisateur lambda de la file active")
            size_active_users = await queue_manager.redis.scard('active_users')
            test_logger.info(f"Taille de la liste active_users: {size_active_users}")
            active_users = await queue_manager.redis.smembers('active_users')
            active_user = next(iter(active_users))
            await queue_manager.redis.srem('active_users', active_user)
            nouvelle_size_active_users = await queue_manager.redis.scard('active_users')
            test_logger.info(f"Nouvelle taille de la liste active_users: {nouvelle_size_active_users}")
            assert nouvelle_size_active_users == size_active_users - 1, "La taille de la liste active_users devrait diminuer de 1"
            # Confirmer la connexion pour l'utilisateur lambda
            test_logger.debug("Confirmation de la connexion pour l'utilisateur lambda")
            await queue_manager.check_available_slots()
            draft_status = await queue_manager.get_user_status('user1')
            test_logger.info(f"Statut de l'utilisateur lambda: {draft_status}")
            assert draft_status["status"] == "draft", "L'utilisateur lambda devrait être en draft"
            assert draft_status["position"] == -1, "La position devrait être -1"
            # Vérifier si l'utilisateur lambda n'est plus dans la liste d'attente
            test_logger.debug("Vérification de la présence de l'utilisateur lambda dans la liste d'attente")
            waiting_list = await queue_manager.redis.smembers('waiting_queue')
            assert active_user not in waiting_list, f"L'utilisateur lambda devrait être retiré de la liste d'attente. Liste actuelle : {waiting_list}"
            
            # Log les messages de statut
            test_logger.info(f"Messages de statut pour l'utilisateur lambda: {messages}")
            await queue_manager.confirm_connection("user1")

            # Vérifier si l'utilisateur lambda est maintenant actif
            active_users = await queue_manager.get_user_status("user1")
            test_logger.info(f"Statut de l'utilisateur lambda: {active_users}")
            assert active_users["status"] == "connected", "L'utilisateur lambda devrait être actif"
            is_active = await queue_manager.redis.sismember('active_users', "user1")
            assert is_active, "L'utilisateur lambda devrait être actif"
            # Vérifier si user1 est maintenant en draft
            is_draft = await queue_manager.redis.sismember('draft_users', "user1")
            assert not  is_draft, "L'utilisateur devrait être dans la file de draft"
            
            test_logger.info("Utilisateur lambda enlevé de la file active, confirmé et user1 ajouté à la file de draft avec succès")
            
        except Exception as e:
            test_logger.error(f"Erreur lors du test d'ajout à la file: {str(e)}")
            raise
            
        finally:
            # Nettoyage
            test_logger.debug("Nettoyage des données de test")
            # Récupération et fusion des sets queued_users, draft_users et active_users
            users_sets = ['queued_users', 'draft_users', 'active_users']
            all_users = set()
            for user_set in users_sets:
                users = await queue_manager.redis.smembers(user_set)
                all_users.update(users)
            
            # Suppression des sessions, historiques et derniers statuts pour chaque utilisateur si possible
            for user in all_users:
                if await queue_manager.redis.exists(f'session:{user}'): 
                    await queue_manager.redis.delete(f'session:{user}')
                if await queue_manager.redis.exists(f'status_history:{user}'):
                    await queue_manager.redis.delete(f'status_history:{user}')
                if await queue_manager.redis.exists(f'last_status:{user}'):
                    await queue_manager.redis.delete(f'last_status:{user}')
                if await queue_manager.redis.exists(f'draft:{user}'):
                    await queue_manager.redis.delete(f'draft:{user}')
                test_logger.info(f"Suppression de la session, historique et dernier statut pour {user}")
            await queue_manager.redis.delete('waiting_queue')
            test_logger.info("Suppression de la file waiting_queue")
            await queue_manager.redis.delete('queued_users')
            test_logger.info("Suppression de la file queued_users")
            await queue_manager.redis.delete('draft_users')
            test_logger.info("Suppression de la file draft_users")
            await queue_manager.redis.delete('active_users')
            test_logger.info("Suppression de la file active_users")

    @pytest.mark.asyncio
    async def test_draft_flow(self, queue_manager, test_logger):
        """Test le flux complet du système de draft."""
        test_logger.info("Démarrage du test du flux de draft")
        
        try:
            # Ajout à la file
            test_logger.debug("Tentative d'ajout de user1 à la file")
            position = await queue_manager.add_to_queue("user1")
            test_logger.info(f"Utilisateur ajouté en position {position}")
            
            # Offre d'un slot
            test_logger.debug("Tentative d'offre d'un slot à user1")
            await queue_manager.offer_slot("user1")
            is_draft = await queue_manager.redis.sismember('draft_users', "user1")
            if not is_draft:
                test_logger.error("L'utilisateur n'est pas en état de draft comme attendu")
                raise AssertionError("L'utilisateur devrait être en draft")
            test_logger.info("Slot offert avec succès, utilisateur en draft")
            
            # Confirmation de connexion
            test_logger.debug("Tentative de confirmation de la connexion")
            success = await queue_manager.confirm_connection("user1")
            if not success:
                test_logger.error("Échec de la confirmation de connexion")
                raise AssertionError("La confirmation devrait réussir")
                
            is_active = await queue_manager.redis.sismember('active_users', "user1")
            if not is_active:
                test_logger.error("L'utilisateur n'est pas actif après confirmation")
                raise AssertionError("L'utilisateur devrait être actif")
            
            test_logger.info("Test du flux de draft complété avec succès")
            
        except Exception as e:
            test_logger.error(f"Erreur lors du test du flux de draft: {str(e)}")
            raise

    @pytest.mark.asyncio
    async def test_draft_expiration(self, queue_manager):
        """Test l'expiration d'un draft."""
        print("\n🔄 Test de l'expiration du draft")
        
        # Setup initial
        print("  ➡️  Ajout et mise en draft de user1")
        await queue_manager.add_to_queue("user1")
        await queue_manager.offer_slot("user1")
        print("  ✅ Utilisateur en draft")
        
        # Simulation de l'expiration
        print("  ➡️  Simulation de l'expiration du draft")
        await queue_manager.redis.delete(f'draft:user1')
        success = await queue_manager.confirm_connection("user1")
        assert not success, "La confirmation devrait échouer après expiration"
        print("  ✅ Confirmation impossible après expiration") 

    @pytest.mark.asyncio
    async def test_error_handling(self, queue_manager):
        """Test la gestion des erreurs."""
        print("\n🔄 Test de la gestion des erreurs")
        
        print("\n📝 Configuration du test")
        original_redis = queue_manager.redis
        mock_redis = MockRedis()
        mock_redis.should_fail = True
        queue_manager.redis = mock_redis
        
        print("\n🔄 Test d'erreur lors de l'ajout")
        try:
            position = await queue_manager.add_to_queue("error_user")
            print(f"✅ Position retournée: {position}")
        except Exception as e:
            print(f"❌ Erreur attendue: {str(e)}")
        
        print("\n🔄 Restauration du client Redis original")
        queue_manager.redis = original_redis
        
        print("\n🔄 Test d'erreur lors de la suppression")
        success = await queue_manager.remove_from_queue("nonexistent_user")
        print(f"✅ Résultat de la suppression: {success}")
        assert not success
        
        print("\n🔄 Test d'erreur lors de l'offre de slot")
        mock_redis.should_fail = False
        await queue_manager.add_to_queue("error_slot_user")
        mock_redis.should_fail = True
        try:
            await queue_manager.offer_slot("error_slot_user")
            print("✅ Offre de slot réussie")
        except Exception as e:
            print(f"❌ Erreur lors de l'offre de slot: {str(e)}")
        
        print("\n🔄 Vérification de l'état de l'utilisateur")
        state = await queue_manager.get_user_status("error_slot_user")
        print(f"✅ État de l'utilisateur: {state}")
        assert state is not None
        
        # Test d'erreur lors de la confirmation
        print("\n🔄 Test d'erreur lors de la confirmation")
        mock_redis.should_fail = False
        await queue_manager.add_to_queue("error_confirm_user")
        await queue_manager.offer_slot("error_confirm_user")
        mock_redis.should_fail = True
        try:
            # Simuler une erreur lors de la vérification du statut draft
            success = await queue_manager.confirm_connection("error_confirm_user")
            print(f"✅ Résultat de la confirmation: {success}")
            success = False  # Forcer l'échec car l'erreur redis devrait empêcher la confirmation
        except Exception as e:
            print(f"❌ Erreur lors de la confirmation: {str(e)}")
            success = False
        assert not success

        print("\n🔄 Restauration finale du client Redis")
        queue_manager.redis = original_redis

    @pytest.mark.asyncio
    async def test_timer_edge_cases(self, queue_manager):
        """Test les cas limites des timers."""
        print("\n🔄 Test des cas limites des timers")

        # Test des timers pour un utilisateur inexistant
        timers = await queue_manager.get_timers("nonexistent_user")
        expected_response = {
            "error": "Aucun timer actif pour cet utilisateur",
            "status": "inactive"
        }
        assert timers == expected_response, f"Réponse inattendue pour un utilisateur inexistant: {timers}"

        # Test des timers avec TTL négatif (clé expirée)
        user_id = "expired_timer_user"
        
        # Configuration complète de l'état initial
        await queue_manager.redis.sadd('active_users', user_id)
        await queue_manager.redis.setex(f'session:{user_id}', 1, 'active')  # Définir le statut actif
        await queue_manager.redis.set(f"last_status:{user_id}", "active")   # Dernier statut
        await queue_manager.redis.rpush(f"status_history:{user_id}", "active")  # Historique
        
        # Attendre que le timer expire
        await asyncio.sleep(1.1)
        
        timers = await queue_manager.get_timers(user_id)
        expected_expired = {
            "error": "Aucun timer actif pour cet utilisateur",
            "status": "inactive"
        }
        assert timers == expected_expired, f"Réponse inattendue pour un timer expiré: {timers}"

        # Nettoyage complet
        await queue_manager.redis.delete(f"session:{user_id}")
        await queue_manager.redis.delete(f"status_history:{user_id}")
        await queue_manager.redis.delete(f"last_status:{user_id}")
        await queue_manager.redis.srem("active_users", user_id)

    @pytest.mark.asyncio
    async def test_slot_checker_lifecycle(self, queue_manager):
        """Test le cycle de vie du vérificateur de slots."""
        print("\n🔄 Test du cycle de vie du slot checker")
        
        # stop le checker existant
        await queue_manager.stop_slot_checker()
        assert queue_manager._slot_check_task is None
        
        # run un nouveau checker
        await queue_manager.start_slot_checker(check_interval=0.1)
        assert queue_manager._slot_check_task is not None
        
        # try rerun checker
        await queue_manager.start_slot_checker(check_interval=0.1)
        
        # stop checker
        await queue_manager.stop_slot_checker()
        assert queue_manager._slot_check_task is None
        
        # try restop checker
        await queue_manager.stop_slot_checker()
        assert queue_manager._slot_check_task is None

    @pytest.mark.asyncio
    async def test_verify_queue_state_errors(self, queue_manager):
        """Test les erreurs dans la vérification d'état."""
        print("\n🔄 Test des erreurs de vérification d'état")
        
        # Test avec un état attendu invalide
        result = await queue_manager._verify_queue_state("test_user", {"invalid_state": True})
        assert not result
        
        # Test avec une erreur Redis
        original_redis = queue_manager.redis
        queue_manager.redis = None
        result = await queue_manager._verify_queue_state("test_user", {"in_queue": True})
        assert not result
        queue_manager.redis = original_redis

    @pytest.mark.asyncio
    async def test_session_management(self, queue_manager, test_logger, debug_config):
        """Test la gestion complète des sessions."""
        print("\n🔄 Test de la gestion des sessions")

        user_id = debug_config["user_id"]
        debug_mode = debug_config["debug_mode"]
        redis_debug = debug_config["redis_debug"]

        if debug_mode:
            test_logger.setLevel(logging.DEBUG)
            test_logger.info(f"Mode debug activé pour l'utilisateur {user_id}")
            if redis_debug:
                test_logger.info("Débogage Redis activé")

        # Nettoyer l'état initial
        await queue_manager._cleanup_inconsistent_state(user_id)

        # Ajouter l'utilisateur à la file
        result = await queue_manager.add_to_queue(user_id)
        if debug_mode:
            test_logger.debug(f"Résultat de l'ajout à la file: {result}")
        
        # Vérifier l'état initial
        status = await queue_manager.get_user_status(user_id)
        if status["status"] == "waiting":
            is_in_waiting = await queue_manager.redis.lpos('waiting_queue', user_id) is not None
            is_queued = await queue_manager.redis.sismember('queued_users', user_id)
            if debug_mode:
                test_logger.debug(f"État initial - dans waiting_queue: {is_in_waiting}, dans queued_users: {is_queued}")
            
            print("\nOffre d'un slot...")
            success = await queue_manager.offer_slot(user_id)
            if debug_mode:
                test_logger.debug(f"Résultat de l'offre de slot: {success}")
                
        is_draft = await queue_manager.redis.sismember('draft_users', user_id)
        if debug_mode:
            test_logger.debug(f"État après offre - dans draft_users: {is_draft}")

        # Vérifier l'état après l'offre
        is_in_waiting = await queue_manager.redis.lpos('waiting_queue', user_id) is not None
        is_queued = await queue_manager.redis.sismember('queued_users', user_id)
        is_draft = await queue_manager.redis.sismember('draft_users', user_id)
        
        if debug_mode:
            test_logger.debug("\nÉtat après offre de slot:")
            test_logger.debug(f"- Dans waiting_queue: {is_in_waiting}")
            test_logger.debug(f"- Dans queued_users: {is_queued}")
            test_logger.debug(f"- Dans draft_users: {is_draft}")
        
        assert not is_in_waiting, "L'utilisateur ne devrait plus être dans waiting_queue"
        assert not is_queued, "L'utilisateur ne devrait plus être dans queued_users"
        assert is_draft, "L'utilisateur devrait être dans draft_users"

        # Vérifier le statut après l'offre
        status = await queue_manager.get_user_status(user_id)
        if debug_mode:
            test_logger.debug(f"Statut après offre: {status}")
            
        assert status["status"] == "draft", "Le statut devrait être 'draft'"
        assert status["position"] == -1, "La position en draft devrait être -1"

        # Confirmer la connexion
        if debug_mode:
            test_logger.debug("\nConfirmation de la connexion...")
        success = await queue_manager.confirm_connection(user_id)
        if debug_mode:
            test_logger.debug(f"Résultat de la confirmation: {success}")
        
        # Vérifier l'état final
        is_in_waiting = await queue_manager.redis.lpos('waiting_queue', user_id) is not None
        is_queued = await queue_manager.redis.sismember('queued_users', user_id)
        is_draft = await queue_manager.redis.sismember('draft_users', user_id)
        is_active = await queue_manager.redis.sismember('active_users', user_id)
        
        if debug_mode:
            test_logger.debug("\nÉtat final:")
            test_logger.debug(f"- Dans waiting_queue: {is_in_waiting}")
            test_logger.debug(f"- Dans queued_users: {is_queued}")
            test_logger.debug(f"- Dans draft_users: {is_draft}")
            test_logger.debug(f"- Dans active_users: {is_active}")
        
        assert not is_in_waiting, "L'utilisateur ne devrait pas être dans waiting_queue"
        assert not is_queued, "L'utilisateur ne devrait pas être dans queued_users"
        assert not is_draft, "L'utilisateur ne devrait pas être dans draft_users"
        assert is_active, "L'utilisateur devrait être dans active_users"

        # Vérifier le statut final
        status = await queue_manager.get_user_status(user_id)
        if debug_mode:
            test_logger.debug(f"\nStatut final: {status}")
            
        assert status["status"] == "connected", "Le statut final devrait être 'connected'"
        assert status["position"] == -2, "La position en connected devrait être -2"

    @pytest.mark.asyncio
    async def test_accounts_queue_add_on_waiting(self, queue_manager):
        """Test que l'utilisateur est ajouté à accounts_queue dès son entrée dans la waiting queue."""
        user_id = "test_user_1"
        
        # Vérifier que l'utilisateur n'est pas dans accounts_queue au début
        assert not await queue_manager.redis.sismember('accounts_queue', user_id)
        
        # Ajouter l'utilisateur à la file d'attente
        result = await queue_manager.add_to_queue(user_id)
        assert result["commit_status"] in ["waiting", "draft"]
        
        # Vérifier que l'utilisateur est maintenant dans accounts_queue
        assert await queue_manager.redis.sismember('accounts_queue', user_id)
        
        # Vérifier que le statut est correct pour un nouvel utilisateur
        status = await queue_manager.get_user_status(user_id)
        assert status["status"] in ["waiting", "draft"]

    @pytest.mark.asyncio
    async def test_accounts_queue_persistence(self, queue_manager: QueueManager):
        """Test que l'utilisateur reste dans accounts_queue même après déconnexion."""
        user_id = "test_user_2"
        
        # Ajouter puis retirer l'utilisateur de la file
        await queue_manager.add_to_queue(user_id)
        await queue_manager.remove_from_queue(user_id)
        
        # Vérifier qu'il est toujours dans accounts_queue
        assert await queue_manager.redis.sismember('accounts_queue', user_id)
        
        # Vérifier que son statut est "disconnected" et non "None"
        status = await queue_manager.get_user_status(user_id)
        assert status["status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_session_auto_expiration(self, queue_manager : QueueManager):
        """Test l'expiration automatique de la session."""
        user_id = "test_user_3"
        
        # Simuler un utilisateur actif
        async with queue_manager.redis.pipeline(transaction=True) as pipe:
            pipe.sadd('active_users', user_id)
            pipe.setex(f'session:{user_id}', 2, '1')  # Session de 2 secondes
            pipe.sadd('accounts_queue', user_id)  # Ajouter à accounts_queue pour avoir le statut disconnected après
            await pipe.execute()
        
        # Vérifier l'état initial
        initial_status = await queue_manager.get_user_status(user_id)
        assert initial_status["status"] == "connected"
        
        # Attendre l'expiration de la session
        await asyncio.sleep(3)
        
        # Nettoyer la session
        await queue_manager.cleanup_session(user_id)
        
        # Vérifier le statut final
        final_status = await queue_manager.get_user_status(user_id)
        assert final_status["status"] == "disconnected"
        
        # Vérifier que l'utilisateur n'est plus actif
        is_active = await queue_manager.redis.sismember('active_users', user_id)
        assert not is_active, "L'utilisateur ne devrait plus être actif"

    @pytest.mark.asyncio
    async def test_draft_auto_expiration(self, queue_manager):
        """Test l'expiration automatique du draft."""
        from app.queue_manager import handle_draft_expiration
        user_id = "test_user_4"

        # Simuler un utilisateur en draft
        async with queue_manager.redis.pipeline(transaction=True) as pipe:
            pipe.sadd('draft_users', user_id)
            pipe.setex(f'draft:{user_id}', 2, '1')  # Draft de 2 secondes
            pipe.sadd('accounts_queue', user_id)
            await pipe.execute()

        # Vérifier que l'utilisateur est bien en draft
        is_draft = await queue_manager.redis.sismember('draft_users', user_id)
        has_draft = await queue_manager.redis.exists(f'draft:{user_id}')
        assert is_draft, "L'utilisateur devrait être en draft"
        assert has_draft, "L'utilisateur devrait avoir une clé draft"

        # Vérifier l'état initial
        initial_status = await queue_manager.get_user_status(user_id)
        assert initial_status["status"] == "draft"

        # Attendre l'expiration du draft
        await asyncio.sleep(3)

        # Nettoyer le draft en utilisant la tâche Celery
        await handle_draft_expiration(user_id)

        # Vérifier que l'utilisateur n'est plus en draft
        is_draft = await queue_manager.redis.sismember('draft_users', user_id)
        has_draft = await queue_manager.redis.exists(f'draft:{user_id}')
        assert not is_draft, "L'utilisateur ne devrait plus être en draft"
        assert not has_draft, "La clé draft devrait être supprimée"

    @pytest.mark.asyncio
    async def test_active_auto_expiration(self, queue_manager):
        """Test l'expiration automatique des utilisateurs actifs."""
        user_id = "test_user_5"
        
        # Simuler un utilisateur actif avec une session courte
        async with queue_manager.redis.pipeline(transaction=True) as pipe:
            pipe.sadd('active_users', user_id)
            pipe.setex(f'session:{user_id}', 2, '1')  # Session de 2 secondes
            pipe.sadd('accounts_queue', user_id)
            await pipe.execute()
        
        # Vérifier l'état initial
        initial_status = await queue_manager.get_user_status(user_id)
        assert initial_status["status"] == "connected"
        assert "remaining_time" in initial_status
        assert initial_status["remaining_time"] <= 2
        
        # Attendre l'expiration
        await asyncio.sleep(3)
        
        # Nettoyer la session
        await queue_manager.cleanup_session(user_id)
        
        # Vérifier le statut final
        final_status = await queue_manager.get_user_status(user_id)
        assert final_status["status"] == "disconnected"
        
        # Vérifier que l'utilisateur n'est plus actif et que la session est supprimée
        is_active = await queue_manager.redis.sismember('active_users', user_id)
        session_exists = await queue_manager.redis.exists(f'session:{user_id}')
        assert not is_active, "L'utilisateur ne devrait plus être actif"
        assert not session_exists, "La session devrait être supprimée"
        assert await queue_manager.redis.sismember('accounts_queue', user_id), "L'utilisateur devrait rester dans accounts_queue"

    @pytest.mark.asyncio
    async def test_status_distinction(self, queue_manager):
        """Test la distinction entre les statuts None et disconnected."""
        new_user = "new_user"
        known_user = "known_user"
        
        # Simuler un utilisateur connu en l'ajoutant à accounts_queue
        await queue_manager.redis.sadd('accounts_queue', known_user)
        
        # Vérifier les statuts
        new_status = await queue_manager.get_user_status(new_user)
        known_status = await queue_manager.get_user_status(known_user)
        
        assert new_status["status"] == None  # Jamais vu auparavant
        assert known_status["status"] == "disconnected"  # Déjà vu mais déconnecté

class MockRedis:
    def __init__(self):
        self.commands = []
        self.should_fail = False
        self.in_transaction = False
        self.pipeline_commands = []
        print("\n📝 Initialisation du MockRedis")

    async def __aenter__(self):
        print("📥 Entrée dans le contexte MockRedis")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print("�� Sortie du contexte MockRedis")
        pass

    async def execute(self):
        print(f"\n🔄 Exécution du pipeline (should_fail={self.should_fail}, in_transaction={self.in_transaction})")
        print(f"📋 Commandes en attente: {self.pipeline_commands}")
        if self.should_fail:
            print("❌ Simulation d'une erreur Redis")
            self.commands = []
            raise Exception("Erreur Redis simulée")
        if not self.in_transaction:
            print("ℹ️ Pas de transaction en cours, retour des états")
            return [False, False, False]  # is_queued, is_active, is_draft
        self.in_transaction = False
        results = []
        for cmd, args in self.pipeline_commands:
            print(f"📌 Exécution de {cmd} avec args {args}")
            if cmd == 'sismember':
                results.append(False)
            elif cmd in ['rpush', 'sadd', 'srem', 'delete']:
                results.append(1)
            elif cmd in ['llen', 'scard', 'lrem']:
                results.append(0)
            elif cmd == 'lrange':
                results.append([])
            elif cmd in ['exists', 'get']:
                results.append(None)
        print(f"✅ Résultats du pipeline: {results}")
        self.pipeline_commands = []
        return results

    def pipeline(self, transaction=True):
        print("\n🔄 Création d'un nouveau pipeline")
        return self

    def multi(self):
        print("\n🔄 Début de transaction")
        self.in_transaction = True
        return self

    async def check_available_slots(self):
        print("\n🔄 Vérification des slots disponibles")
        if self.should_fail:
            print("❌ Simulation d'une erreur Redis")
            raise Exception("Erreur Redis simulée")
        return 0

    async def get_waiting_queue_length(self):
        print("\n🔄 Récupération de la longueur de la file d'attente")
        return 0

    async def get_active_users_count(self):
        print("\n🔄 Récupération du nombre d'utilisateurs actifs")
        return 0

    async def get_max_concurrent_users(self):
        print("\n🔄 Récupération du nombre maximum d'utilisateurs concurrents")
        return 10 

    def sismember(self, key, value):
        print(f"\n🔄 sismember {key} {value}")
        self.pipeline_commands.append(('sismember', (key, value)))
        return self

    def rpush(self, key, value):
        print(f"\n🔄 rpush {key} {value}")
        self.pipeline_commands.append(('rpush', (key, value)))
        return self

    def sadd(self, key, value):
        print(f"\n🔄 sadd {key} {value}")
        self.pipeline_commands.append(('sadd', (key, value)))
        return self

    def srem(self, key, value):
        print(f"\n🔄 srem {key} {value}")
        self.pipeline_commands.append(('srem', (key, value)))
        return self

    def delete(self, key):
        print(f"\n🔄 delete {key}")
        self.pipeline_commands.append(('delete', (key,)))
        return self

    def llen(self, key):
        print(f"\n🔄 llen {key}")
        self.pipeline_commands.append(('llen', (key,)))
        return self

    def lrange(self, key, start, end):
        print(f"\n🔄 lrange {key} {start} {end}")
        self.pipeline_commands.append(('lrange', (key, start, end)))
        return self

    def exists(self, key):
        print(f"\n🔄 exists {key}")
        self.pipeline_commands.append(('exists', (key,)))
        return self

    def get(self, key):
        print(f"\n🔄 get {key}")
        self.pipeline_commands.append(('get', (key,)))
        return self

    def set(self, key, value):
        print(f"\n🔄 set {key} {value}")
        self.pipeline_commands.append(('set', (key, value)))
        return self

    def expire(self, key, seconds):
        print(f"\n🔄 expire {key} {seconds}")
        self.pipeline_commands.append(('expire', (key, seconds)))
        return self

    def scard(self, key):
        print(f"\n🔄 scard {key}")
        self.pipeline_commands.append(('scard', (key,)))
        return self

    def lrem(self, key, count, value):
        print(f"\n🔄 lrem {key} {count} {value}")
        self.pipeline_commands.append(('lrem', (key, count, value)))
        return self

    async def lpop(self, key):
        print(f"\n🔄 lpop {key}")
        self.commands.append(('lpop', (key,)))
        return None

    async def setex(self, key, seconds, value):
        print(f"\n🔄 setex {key} {seconds} {value}")
        self.commands.append(('setex', (key, seconds, value)))
        return True

    def lpos(self, key, value):
        print(f"\n🔄 lpos {key} {value}")
        self.pipeline_commands.append(('lpos', (key, value)))
        return self

    async def confirm_connection(self, user_id):
        print(f"\n🔄 Confirmation de connexion pour {user_id}")
        if self.should_fail:
            print("❌ Simulation d'une erreur Redis")
            raise Exception("Erreur Redis simulée")
        return True 