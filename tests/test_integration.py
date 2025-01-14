import pytest
import asyncio
from app.queue_manager import QueueManager
from redis.exceptions import RedisError
import logging

class TestIntegration:
    @pytest.mark.asyncio
    async def test_concurrent_users(self, redis_client, test_logger):
        """Test l'ajout concurrent d'utilisateurs."""
        test_logger.info("Démarrage du test d'ajout concurrent")
        
        try:
            # Nettoyage initial
            await redis_client.flushdb()
            test_logger.debug("Base de données nettoyée")
            
            queue_manager = QueueManager(redis_client)
            users = [f"user_{i}" for i in range(5)]
            test_logger.info(f"Ajout concurrent de {len(users)} utilisateurs")
            
            # Add users concurrently with check_slots=False
            tasks = [queue_manager.add_to_queue(user, check_slots=False) for user in users]
            results = await asyncio.gather(*tasks)
            test_logger.debug(f"Résultats des ajouts: {results}")
            
            # Vérification immédiate après l'ajout
            queue_size = await redis_client.llen("waiting_queue")
            queued_users = await redis_client.smembers("queued_users")
            test_logger.info(f"État immédiat - File d'attente: {queue_size}, Utilisateurs en file: {len(queued_users)}")
            
            # Vérification que tous les utilisateurs sont bien ajoutés
            assert queue_size == 5, "La file d'attente devrait contenir 5 utilisateurs"
            assert len(queued_users) == 5, "queued_users devrait contenir 5 utilisateurs"
            
            # Vérification de chaque utilisateur individuellement
            for user in users:
                is_queued = await redis_client.sismember("queued_users", user)
                is_in_waiting = await redis_client.lpos("waiting_queue", user) is not None
                test_logger.debug(f"État de {user}: queued={is_queued}, in_waiting={is_in_waiting}")
                assert is_queued, f"L'utilisateur {user} devrait être dans queued_users"
                assert is_in_waiting, f"L'utilisateur {user} devrait être dans waiting_queue"
            
            # Maintenant on peut vérifier les slots manuellement
            test_logger.info("Vérification manuelle des slots")
            await queue_manager.check_available_slots()
            
            # Vérification finale après l'offre de slots
            final_queue_size = await redis_client.llen("waiting_queue")
            final_queued_users = await redis_client.smembers("queued_users")
            final_draft_users = await redis_client.smembers("draft_users")
            test_logger.info(f"État final - File: {final_queue_size}, Queued: {len(final_queued_users)}, Draft: {len(final_draft_users)}")
            
        except RedisError as e:
            test_logger.error(f"Erreur Redis: {str(e)}")
            pytest.fail(f"Redis error: {str(e)}")
        finally:
            # cleanup
            test_logger.debug("Nettoyage des données de test")
            await redis_client.delete("waiting_queue")
            await redis_client.delete("queued_users")
            await redis_client.delete("draft_users")
            for user in users:
                await redis_client.delete(f"status_history:{user}")
                await redis_client.delete(f"last_status:{user}")
                await redis_client.delete(f"draft:{user}")

    @pytest.mark.asyncio
    async def test_requeue_mechanism(self, redis_client, test_logger):
        """Test le mécanisme de remise en file d'attente."""
        test_logger.info("Démarrage du test de remise en file d'attente")
        
        try:
            # Nettoyage initial
            await redis_client.flushdb()
            test_logger.debug("Base de données nettoyée")
            
            queue_manager = QueueManager(redis_client)
            user_id = "test_user_requeue"
            
            # init queue with check_slots=False
            test_logger.info(f"Ajout de l'utilisateur {user_id} à la file")
            result = await queue_manager.add_to_queue(user_id, check_slots=False)
            test_logger.debug(f"Résultat de l'ajout: {result}")
            
            # Vérification immédiate après l'ajout
            is_queued = await redis_client.sismember("queued_users", user_id)
            is_in_waiting = await redis_client.lpos("waiting_queue", user_id) is not None
            test_logger.info(f"État immédiat - queued={is_queued}, in_waiting={is_in_waiting}")
            
            assert is_queued, "L'utilisateur devrait être dans queued_users"
            assert is_in_waiting, "L'utilisateur devrait être dans waiting_queue"
            
            # offer slot
            test_logger.info("Offre d'un slot à l'utilisateur")
            await queue_manager.offer_slot(user_id)
            
            # Vérification après l'offre
            is_draft = await redis_client.sismember("draft_users", user_id)
            is_queued = await redis_client.sismember("queued_users", user_id)
            is_in_waiting = await redis_client.lpos("waiting_queue", user_id) is not None
            test_logger.info(f"État après offre - draft={is_draft}, queued={is_queued}, in_waiting={is_in_waiting}")
            
            assert is_draft, "L'utilisateur devrait être dans draft_users"
            assert not is_queued, "L'utilisateur ne devrait plus être dans queued_users"
            assert not is_in_waiting, "L'utilisateur ne devrait plus être dans waiting_queue"
            
            # let draft expire
            test_logger.info("Simulation de l'expiration du draft")
            await redis_client.delete(f"draft:{user_id}")
            await redis_client.srem("draft_users", user_id)
            
            # Vérification après expiration
            is_draft = await redis_client.sismember("draft_users", user_id)
            test_logger.info(f"État après expiration - draft={is_draft}")
            assert not is_draft, "L'utilisateur ne devrait plus être dans draft_users"
            
        except RedisError as e:
            test_logger.error(f"Erreur Redis: {str(e)}")
            pytest.fail(f"Redis error: {str(e)}")
        finally:
            # Cleanup
            test_logger.debug("Nettoyage des données de test")
            await redis_client.delete("waiting_queue")
            await redis_client.delete("queued_users")
            await redis_client.delete(f"draft:{user_id}")
            await redis_client.delete("draft_users")
            await redis_client.delete(f"status_history:{user_id}")
            await redis_client.delete(f"last_status:{user_id}") 