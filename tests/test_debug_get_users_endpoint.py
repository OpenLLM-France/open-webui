import pytest
from app.queue_manager import QueueManager
from httpx import AsyncClient
import logging
import asyncio
import pdb  # Importer le module pdb pour le débogage

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestDebugGetUsersEndpoint:
    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self, redis_client):
        self.redis = redis_client
        yield
        # Nettoyage après chaque test
        await self.redis.flushall()

    @pytest.mark.asyncio
    async def test_get_users_endpoint_debug(self, test_client, queue_manager, test_logger):
        """Test l'endpoint /queue/get_users en mode débogage."""
        test_logger.info("Démarrage du test de l'endpoint get_users en mode débogage")
        
        # Nettoyer Redis
        await queue_manager.redis.flushdb()
        test_logger.info("Redis nettoyé")
        
        # Arrêter le vérificateur automatique
        await queue_manager.stop_slot_checker()
        test_logger.info("Vérificateur automatique arrêté")
        
        # Vérifier l'état initial des files
        response = await test_client.get("/queue/get_users")
        assert response.status_code == 200
        initial_data = response.json()
        test_logger.info(f"État initial des files: {initial_data}")
        
        # Point de débogage
        pdb.set_trace()
        
        # 1. Ajouter et confirmer le premier utilisateur actif
        user_active = "user_active_1"
        response = await test_client.post(f"/queue/join/{user_active}")
        assert response.status_code == 200
        test_logger.info(f"Utilisateur {user_active} ajouté")
        
        # Forcer la vérification des slots pour le passage en draft
        await queue_manager.check_available_slots()
        test_logger.info("Vérification forcée des slots pour passage en draft")
        
        # Vérifier l'état des files
        response = await test_client.get("/queue/get_users")
        assert response.status_code == 200
        data = response.json()
        test_logger.info(f"État des files après check_slots: {data}")
        
        # Confirmer la connexion
        response = await test_client.post(f"/queue/confirm/{user_active}")
        assert response.status_code == 200
        test_logger.info(f"Connexion confirmée pour {user_active}")
        
        # Vérifier l'état après confirmation
        response = await test_client.get("/queue/get_users")
        assert response.status_code == 200
        data = response.json()
        test_logger.info(f"État des files après confirmation: {data}")
        assert len(data["active_users"]) == 1, "Devrait avoir 1 utilisateur actif"
        
        # 2. Ajouter 5 utilisateurs en attente
        waiting_users = []
        for i in range(5):
            user_id = f"user_wait_{i}"
            waiting_users.append(user_id)
            response = await test_client.post(f"/queue/join/{user_id}")
            assert response.status_code == 200
            test_logger.info(f"Utilisateur {user_id} ajouté à la file d'attente")
        
        # Vérifier l'état après ajout des utilisateurs en attente
        response = await test_client.get("/queue/get_users")
        assert response.status_code == 200
        data = response.json()
        test_logger.info(f"État des files après ajout des utilisateurs en attente: {data}")
        assert len(data["waiting_users"]) == 5, "Devrait avoir 5 utilisateurs en attente"
        assert len(data["active_users"]) == 1, "Devrait toujours avoir 1 utilisateur actif"
        
        # 3. Forcer une vérification des slots
        await queue_manager.check_available_slots()
        test_logger.info("Vérification forcée finale des slots")
        
        # Vérifier l'état final
        response = await test_client.get("/queue/get_users")
        assert response.status_code == 200
        final_data = response.json()
        test_logger.info(f"État final des files: {final_data}")
        
        # Vérifier les nombres d'utilisateurs dans chaque état
        assert len(final_data["waiting_users"]) == 4, "Devrait avoir 4 utilisateurs en attente"
        assert len(final_data["draft_users"]) == 1, "Devrait avoir 1 utilisateur en draft"
        assert len(final_data["active_users"]) == 1, "Devrait avoir 1 utilisateur actif"
        
        # Nettoyer Redis à la fin du test
        await queue_manager.redis.flushdb()
        test_logger.info("Base Redis nettoyée") 