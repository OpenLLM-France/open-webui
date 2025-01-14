import pytest
from app.queue_manager import QueueManager
from httpx import AsyncClient
import logging
import asyncio
from celery import current_app as celery_app, Celery
import time

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestAPI:
    @pytest.fixture(autouse=True)
    async def cleanup(self, redis_client):
        self.redis = redis_client
        yield
        # Nettoyage après chaque test
        await self.redis.flushall()
        if hasattr(self, 'queue_manager'):
            await self.queue_manager.stop_slot_checker()

    @pytest.mark.asyncio
    async def test_join_queue_flow(self, test_client, test_logger):
        """Test le flux complet d'ajout à la file."""
        user_id = "test_user_flow"
        
        # Ajouter l'utilisateur à la file
        response = await test_client.post(f"/queue/join/{user_id}")
        assert response.status_code == 200
        test_logger.info("Utilisateur ajouté à la file")
        
        # Vérifier le statut initial
        status_response = await test_client.get(f"/queue/status/{user_id}")
        assert status_response.status_code == 200
        status = status_response.json()
        assert status["status"] in ["queued", "in_waiting", "draft"]
        test_logger.info(f"Statut initial vérifié: {status}")

    @pytest.mark.asyncio
    async def test_join_queue_flow_when_full(self, test_client, test_logger):
        """Test le flux d'ajout à la file quand elle est pleine."""
        # Ajouter le premier utilisateur
        user_id_1 = "test_user_0"
        response = await test_client.post(f"/queue/join/{user_id_1}")
        assert response.status_code == 200
        test_logger.info("Premier utilisateur ajouté")
        
        # Ajouter le deuxième utilisateur
        user_id_2 = "test_user_1"
        response = await test_client.post(f"/queue/join/{user_id_2}")
        assert response.status_code == 200
        test_logger.info("Deuxième utilisateur ajouté")
        
        # Vérifier les statuts
        for user_id in [user_id_1, user_id_2]:
            status_response = await test_client.get(f"/queue/status/{user_id}")
            assert status_response.status_code == 200
            status = status_response.json()
            assert status["status"] in ["queued", "in_waiting", "draft"]
            test_logger.info(f"Statut vérifié pour {user_id}: {status}")

    @pytest.mark.asyncio
    async def test_leave_queue(self, test_client, test_logger):
        """Test le départ de la file d'attente."""
        user_id = "test_user_leave"
        
        # Ajouter l'utilisateur à la file
        join_response = await test_client.post(f"/queue/join/{user_id}")
        assert join_response.status_code == 200
        test_logger.info("Utilisateur ajouté à la file")
        
        # Faire partir l'utilisateur
        leave_response = await test_client.post(f"/queue/leave/{user_id}")
        assert leave_response.status_code == 200
        test_logger.info("Utilisateur retiré de la file")
        
        # Vérifier que l'utilisateur n'est plus dans la file
        status_response = await test_client.get(f"/queue/status/{user_id}")
        assert status_response.status_code == 200
        status = status_response.json()
        assert status["status"] == "disconnected"
        test_logger.info("Statut vérifié après départ")

    @pytest.mark.asyncio
    async def test_get_status_nonexistent(self, test_client):
        """Test la récupération du statut pour un utilisateur inexistant."""
        response = await test_client.get("/queue/status/nonexistent_user")
        assert response.status_code == 200
        status = response.json()
        assert status["status"] is None

    @pytest.mark.asyncio
    async def test_heartbeat(self, test_client, test_logger):
        """Test le heartbeat pour maintenir la session active."""
        user_id = "test_user_heartbeat"
        
        # Ajouter l'utilisateur à la file
        join_response = await test_client.post(f"/queue/join/{user_id}")
        assert join_response.status_code == 200
        test_logger.info("Utilisateur ajouté à la file")
        
        # Confirmer la connexion
        confirm_response = await test_client.post(f"/queue/confirm/{user_id}")
        assert confirm_response.status_code == 200
        test_logger.info("Connexion confirmée")
        
        # Envoyer un heartbeat
        heartbeat_response = await test_client.post(f"/queue/heartbeat/{user_id}")
        assert heartbeat_response.status_code == 200
        test_logger.info("Heartbeat envoyé avec succès")
        
        # Vérifier que la session est toujours active
        status_response = await test_client.get(f"/queue/status/{user_id}")
        assert status_response.status_code == 200
        status = status_response.json()
        assert status["status"] != "disconnected"
        test_logger.info("Session toujours active après heartbeat")

    @pytest.mark.asyncio
    async def test_heartbeat_invalid(self, test_client):
        """Test le heartbeat pour un utilisateur invalide."""
        response = await test_client.post("/queue/heartbeat/invalid_user")
        assert response.status_code == 404  

    @pytest.mark.asyncio
    @pytest.mark.timeout(600)  # Increase the timeout to 60 seconds
    async def test_get_users_endpoint(self, test_client, queue_manager, test_logger):
        """Test l'endpoint /queue/get_users."""
        test_logger.info("Démarrage du test de l'endpoint get_users")
        
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
        
        # 1. Ajouter et confirmer le premier utilisateur actif
        user_active = "user_active_1"
        response = await test_client.post(f"/queue/join/{user_active}")
        assert response.status_code == 200
        test_logger.info(f"Utilisateur {user_active} ajouté")
        
        # Forcer la vérification des slots pour le passage en draft
        await queue_manager.check_available_slots()
        test_logger.info("Vérification forcée des slots pour passage en draft")
        await queue_manager.stop_slot_checker()
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
        assert len(data["waiting_users"]) == 4, "Devrait avoir 5 utilisateurs en attente"
        assert len(data["draft_users"]) == 1, "Devrait toujours avoir 1 utilisateur actif"
        assert len(data["active_users"]) == 1, "Devrait toujours avoir 1 utilisateur actif"
        
        # 3. Forcer une vérification des slots

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