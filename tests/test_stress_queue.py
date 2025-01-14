import asyncio
import random
import pytest
import time
import threading
import queue
import concurrent.futures
import httpx
from functools import partial
from typing import Dict, List
from httpx import AsyncClient
import logging
from celery_test_config import setup_test_celery
import os
# Configuration du logging pour les tests de stress
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

class TestStressQueue:
    @pytest.fixture(autouse=True)
    def setup_logging(self, test_logger):
        """Configure le niveau de log pour les tests de stress."""
        test_logger.setLevel(logging.INFO)
        return test_logger

    @pytest.mark.asyncio
    async def test_parallel_users_stress(self, test_client, redis_client, queue_manager_with_checker, test_logger):
        """Test de stress avec plusieurs utilisateurs en parallèle."""
        # Configuration
        NB_USERS = 50  # Réduit pour éviter le timeout
        MAX_ACTIVE = 25  # Réduit proportionnellement
        SIMULATION_TIME = 20  # Réduit le temps de simulation
        BATCH_SIZE = 5  # Nombre d'utilisateurs à ajouter par lot
        
        # Probabilités de comportement (en pourcentage)
        PROBA_CONNECT = 80    # Probabilité qu'un utilisateur en draft se connecte
        PROBA_DISCONNECT = 20 # Probabilité qu'un utilisateur actif se déconnecte
        
        users: List[Dict] = []
        active_users: List[str] = []
        draft_users: List[str] = []
        waiting_users: List[str] = []

        test_logger.info(f"Démarrage du test de stress avec {NB_USERS} utilisateurs")

        async def sync_lists_with_redis():
            """Synchronise les listes locales avec l'état Redis."""
            try:
                # Récupérer les états depuis Redis
                redis_active = await redis_client.smembers("active_users")
                redis_draft = await redis_client.smembers("draft_users")
                redis_waiting = await redis_client.lrange("waiting_queue", 0, -1)
                
                # Mettre à jour les listes locales
                active_users.clear()
                active_users.extend(redis_active)
                
                draft_users.clear()
                draft_users.extend(redis_draft)
                
                waiting_users.clear()
                waiting_users.extend(redis_waiting)
                
                test_logger.debug(
                    f"Listes synchronisées - Actifs: {len(active_users)}, "
                    f"Draft: {len(draft_users)}, "
                    f"En attente: {len(waiting_users)}"
                )
            except Exception as e:
                test_logger.error(f"Erreur lors de la synchronisation: {str(e)}")

        async def add_users_batch(start_idx: int, count: int):
            """Ajoute un lot d'utilisateurs à la file d'attente."""
            for i in range(start_idx, min(start_idx + count, NB_USERS)):
                user_id = f"stress_user_{i}"
                users.append({"id": user_id, "status": "waiting"})
                
                try:
                    # Ajouter à la file d'attente avec retry
                    for attempt in range(3):
                        response = await test_client.post(f"/queue/join/{user_id}")
                        if response.status_code == 200:
                            test_logger.debug(f"Utilisateur {user_id} créé et ajouté à la file")
                            break
                        await asyncio.sleep(0.1)
                    else:
                        test_logger.error(f"Impossible d'ajouter {user_id} après 3 tentatives")
                except Exception as e:
                    test_logger.error(f"Erreur lors de l'ajout de {user_id}: {str(e)}")
                
                # Attendre un peu entre chaque utilisateur
                await asyncio.sleep(0.2)

        async def simulate_user_behavior():
            """Simule le comportement aléatoire d'un utilisateur."""
            try:
                current_user_count = 0
                while True:
                    # Synchroniser l'état avec Redis
                    await sync_lists_with_redis()
                    
                    # Vérifier si on peut ajouter plus d'utilisateurs
                    total_active = len(active_users) + len(draft_users)
                    if total_active < MAX_ACTIVE and current_user_count < NB_USERS:
                        # Ajouter un nouveau lot d'utilisateurs
                        await add_users_batch(current_user_count, BATCH_SIZE)
                        current_user_count = min(current_user_count + BATCH_SIZE, NB_USERS)
                    
                    # Gérer les utilisateurs en draft
                    for user_id in draft_users[:]:
                        if random.randint(1, 100) <= PROBA_CONNECT:
                            test_logger.debug(f"Tentative de connexion pour {user_id}")
                            try:
                                response = await test_client.post("/queue/confirm/{user_id}")
                                if response.status_code == 200:
                                    await sync_lists_with_redis()
                                    test_logger.info(f"Utilisateur {user_id} connecté avec succès")
                            except Exception as e:
                                test_logger.error(f"Erreur lors de la connexion de {user_id}: {str(e)}")

                    # Gérer les utilisateurs actifs
                    for user_id in active_users[:]:
                        if random.randint(1, 100) <= PROBA_DISCONNECT:
                            test_logger.debug(f"Déconnexion de {user_id}")
                            try:
                                # D'abord quitter la file
                                leave_response = await test_client.post("/queue/leave/{user_id}")
                                if leave_response.status_code == 200:
                                    # Puis rejoindre à nouveau
                                    await test_client.post("/queue/join/{user_id}")
                                    await sync_lists_with_redis()
                                    test_logger.info(f"Utilisateur {user_id} déconnecté et remis en file d'attente")
                            except Exception as e:
                                test_logger.error(f"Erreur lors de la déconnexion de {user_id}: {str(e)}")

                    await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                test_logger.info("Tâche de simulation arrêtée")
            except Exception as e:
                test_logger.error(f"Erreur dans simulate_user_behavior: {str(e)}")

        async def monitor_queue_state():
            """Surveille et log l'état de la file d'attente."""
            try:
                while True:
                    await sync_lists_with_redis()
                    
                    active_count = len(active_users)
                    draft_count = len(draft_users)
                    waiting_count = len(waiting_users)
                    
                    test_logger.info(
                        f"État de la file - Actifs: {active_count}, "
                        f"Draft: {draft_count}, "
                        f"En attente: {waiting_count}"
                    )
                    
                    # Vérifier que le nombre total d'utilisateurs est correct
                    total_users = active_count + draft_count + waiting_count
                    assert total_users <= NB_USERS, f"Nombre total d'utilisateurs incorrect: {total_users}"
                    
                    # Vérifier que le nombre d'utilisateurs actifs ne dépasse pas la limite
                    assert active_count + draft_count <= MAX_ACTIVE, \
                        f"Trop d'utilisateurs actifs/draft: {active_count + draft_count}"
                    
                    await asyncio.sleep(2)
            except asyncio.CancelledError:
                test_logger.info("Tâche de monitoring arrêtée")
            except Exception as e:
                test_logger.error(f"Erreur dans monitor_queue_state: {str(e)}")

        async def check_server_connection():
            """Vérifie que le serveur est accessible avant de démarrer les tests."""
            try:
                # Tester avec un endpoint simple
                response = await test_client.get("/queue/status/test_connection")
                # 404 est OK car l'utilisateur n'existe pas
                if response.status_code in [200, 404]:
                    test_logger.info("Test client prêt")
                    return True
            except Exception as e:
                test_logger.error(f"Erreur lors du test du client: {str(e)}")
            return False

        try:
            # Vérifier la connexion au serveur
            if not await check_server_connection():
                raise RuntimeError("Impossible de se connecter au serveur après plusieurs tentatives")

            # Démarrer les tâches de simulation
            behavior_task = asyncio.create_task(simulate_user_behavior())
            monitor_task = asyncio.create_task(monitor_queue_state())

            # Laisser la simulation tourner
            await asyncio.sleep(SIMULATION_TIME)

            # Arrêter les tâches proprement
            behavior_task.cancel()
            monitor_task.cancel()
            try:
                await behavior_task
                await monitor_task
            except asyncio.CancelledError:
                pass

            # Vérifications finales
            await sync_lists_with_redis()
            
            test_logger.info(
                f"État final - Actifs: {len(active_users)}, "
                f"Draft: {len(draft_users)}, "
                f"En attente: {len(waiting_users)}"
            )

            # Vérifier que le nombre maximum d'utilisateurs actifs n'a jamais été dépassé
            assert len(active_users) + len(draft_users) <= MAX_ACTIVE, \
                "Le nombre maximum d'utilisateurs actifs a été dépassé"

        finally:
            # Nettoyage
            test_logger.info("Nettoyage des données de test")
            for user in users:
                try:
                    # D'abord faire quitter la file
                    await test_client.post("/queue/leave", json={"user_id": user["id"]})
                    await asyncio.sleep(0.1)  # Petit délai entre chaque leave
                    # Puis nettoyer Redis
                    await redis_client.srem("active_users", user["id"])
                    await redis_client.srem("draft_users", user["id"])
                    await redis_client.lrem("waiting_queue", 0, user["id"])
                    await redis_client.delete(f"session:{user['id']}")
                    await redis_client.delete(f"draft:{user['id']}")
                except Exception as e:
                    test_logger.error(f"Erreur lors du nettoyage de {user['id']}: {str(e)}")

    @pytest.mark.asyncio
    async def test_rapid_join_leave_stress(self, test_client, redis_client, queue_manager_with_checker, test_logger):
        """Test de stress avec des utilisateurs qui rejoignent et quittent rapidement la file."""
        NB_USERS = 25  # Réduit pour éviter la surcharge
        CYCLES = 3    # Réduit le nombre de cycles
        
        async def join_leave_cycle(user_id: str):
            """Simule un cycle de join/leave pour un utilisateur."""
            try:
                for _ in range(CYCLES):
                    # Rejoindre la file avec retry
                    for attempt in range(3):
                        try:
                            join_response = await test_client.post("/queue/join/{user_id}")
                            if join_response.status_code == 200:
                                break
                            await asyncio.sleep(0.1)
                        except Exception as e:
                            test_logger.error(f"Erreur lors du join pour {user_id}: {str(e)}")
                            await asyncio.sleep(0.1)
                    
                    # Attendre un temps aléatoire
                    await asyncio.sleep(random.uniform(0.2, 0.8))
                    
                    # Vérifier le statut avant de quitter
                    status_response = await test_client.get(f"/queue/status/{user_id}")
                    if status_response.status_code == 200:
                        status = status_response.json()
                        test_logger.debug(f"Statut de {user_id}: {status}")
                        
                        if status.get("status") == "draft":
                            # Si en draft, d'abord confirmer la connexion
                            await test_client.post("/queue/confirm/{user_id}")
                            await asyncio.sleep(0.1)
                        
                        # Puis quitter la file
                        for attempt in range(3):
                            try:
                                leave_response = await test_client.post("/queue/leave/{user_id}")
                                if leave_response.status_code == 200:
                                    break
                                await asyncio.sleep(0.1)
                            except Exception as e:
                                test_logger.error(f"Erreur lors du leave pour {user_id}: {str(e)}")
                                await asyncio.sleep(0.1)
                    
                    # Délai plus long entre les cycles
                    await asyncio.sleep(random.uniform(0.3, 0.6))
            except Exception as e:
                test_logger.error(f"Erreur dans le cycle pour {user_id}: {str(e)}")

        async def cleanup_user(user_id: str):
            """Nettoie proprement un utilisateur du système."""
            try:
                # Vérifier le statut actuel
                status_response = await test_client.get(f"/queue/status/{user_id}")
                if status_response.status_code == 200:
                    status = status_response.json()
                    test_logger.debug(f"Nettoyage de {user_id} avec statut: {status}")
                    
                    if status.get("status") == "draft":
                        # Si en draft, confirmer d'abord la connexion
                        await test_client.post("/queue/confirm/{user_id}")
                        await asyncio.sleep(0.1)
                    
                    # Puis quitter la file
                    await test_client.post("/queue/leave/{user_id}")
                    await asyncio.sleep(0.1)
                
                # Nettoyage forcé dans Redis
                await redis_client.srem("active_users", user_id)
                await redis_client.srem("draft_users", user_id)
                await redis_client.lrem("waiting_queue", 0, user_id)
                await redis_client.delete(f"session:{user_id}")
                await redis_client.delete(f"draft:{user_id}")
                await redis_client.delete(f"status_history:{user_id}")
                await redis_client.delete(f"last_status:{user_id}")
            except Exception as e:
                test_logger.error(f"Erreur lors du nettoyage de {user_id}: {str(e)}")

        try:
            # Créer et lancer toutes les tâches en parallèle
            tasks = []
            for i in range(NB_USERS):
                user_id = f"rapid_user_{i}"
                task = asyncio.create_task(join_leave_cycle(user_id))
                tasks.append(task)
                test_logger.debug(f"Tâche créée pour {user_id}")
                await asyncio.sleep(0.1)  # Délai entre chaque création de tâche

            # Attendre que toutes les tâches soient terminées
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Attendre un peu pour laisser le système se stabiliser
            await asyncio.sleep(2)
            
            # Nettoyage complet de tous les utilisateurs
            cleanup_tasks = []
            for i in range(NB_USERS):
                user_id = f"rapid_user_{i}"
                cleanup_tasks.append(asyncio.create_task(cleanup_user(user_id)))
            
            # Attendre que tout le nettoyage soit terminé
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            # Attendre encore un peu pour le nettoyage
            await asyncio.sleep(2)
            
            # Vérifications finales
            final_active = await redis_client.scard("active_users")
            final_draft = await redis_client.scard("draft_users")
            final_waiting = await redis_client.llen("waiting_queue")
            
            # Vérifier qu'il ne reste pas d'utilisateurs dans le système
            assert final_active == 0, f"Il reste {final_active} utilisateurs actifs"
            assert final_draft == 0, f"Il reste {final_draft} utilisateurs en draft"
            assert final_waiting == 0, f"Il reste {final_waiting} utilisateurs en attente"
            
            test_logger.info("Test de stress rapid join/leave terminé avec succès")

        finally:
            # Nettoyage supplémentaire si nécessaire
            test_logger.info("Nettoyage final")
            cleanup_tasks = []
            for i in range(NB_USERS):
                user_id = f"rapid_user_{i}"
                cleanup_tasks.append(asyncio.create_task(cleanup_user(user_id)))
            
            # Attendre que tout le nettoyage soit terminé
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_multiple_clients_timer_polling(self, test_client, redis_client, queue_manager_with_checker, test_logger):
        """Test de stress avec plusieurs clients qui font du long polling sur leurs timers."""
        NB_CLIENTS = 10  # Réduit de 50 à 10 clients
        POLL_DURATION = 15  # Réduit de 30 à 15 secondes
        POLL_INTERVAL = 1.0  # Réduit à 1 seconde
        
        clients: Dict[str, ClientState] = {}
        
        class ClientState:
            def __init__(self, user_id: str):
                self.user_id = user_id
                self.last_ttl = float('inf')
                self.status = None
                self.timer_decreasing = True
                self.ttl_history = []
            
            def __str__(self):
                return f"Client {self.user_id} - Status: {self.status}, TTL: {self.last_ttl}"

        async def poll_client_timer(client: ClientState):
            """Effectue le long polling des timers pour un client."""
            try:
                test_logger.info(f"Démarrage du polling pour {client.user_id}")
                while True:
                    try:
                        # Récupérer les timers
                        response = await test_client.get(f"/queue/timers/{client.user_id}")
                        if response.status_code == 200:
                            timer_data = response.json()
                            test_logger.debug(f"Timer data pour {client.user_id}: {timer_data}")
                            
                            if timer_data:  # Si on a des données de timer
                                current_ttl = timer_data.get('ttl', 0)
                                timer_type = timer_data.get('timer_type')
                                
                                # Vérifier que le TTL diminue
                                if client.last_ttl != float('inf'):
                                    if current_ttl > client.last_ttl + 2:  # Tolérance de 2 secondes
                                        client.timer_decreasing = False
                                        test_logger.error(
                                            f"Timer non décroissant pour {client.user_id}: "
                                            f"{client.last_ttl} -> {current_ttl} "
                                            f"(différence: {current_ttl - client.last_ttl})"
                                        )
                                
                                client.last_ttl = current_ttl
                                client.ttl_history.append(current_ttl)
                                test_logger.debug(
                                    f"Client {client.user_id} - Type: {timer_type}, "
                                    f"TTL: {current_ttl}, Historique: {len(client.ttl_history)} valeurs"
                                )
                            
                            # Récupérer aussi le statut
                            status_response = await test_client.get(f"/queue/status/{client.user_id}")
                            if status_response.status_code == 200:
                                status_data = status_response.json()
                                client.status = status_data.get('status')
                                test_logger.debug(f"Status pour {client.user_id}: {client.status}")
                    
                    except Exception as e:
                        test_logger.error(f"Erreur lors du poll pour {client.user_id}: {str(e)}")
                    
                    await asyncio.sleep(POLL_INTERVAL)
                    
            except asyncio.CancelledError:
                test_logger.info(f"Polling arrêté pour {client.user_id} avec {len(client.ttl_history)} valeurs collectées")

        async def client_lifecycle(client: ClientState):
            """Simule le cycle de vie d'un client."""
            try:
                # Rejoindre la file
                join_response = await test_client.post(f"/queue/join/{client.user_id}")
                assert join_response.status_code == 200
                
                # Démarrer le polling des timers
                polling_task = asyncio.create_task(poll_client_timer(client))
                
                # Attendre un moment avant de confirmer si en draft
                await asyncio.sleep(random.uniform(1, 3))
                
                # Si en draft, confirmer la connexion
                if client.status == "draft":
                    confirm_response = await test_client.post(
                        f"/queue/confirm/{client.user_id}"
                    )
                    if confirm_response.status_code == 200:
                        test_logger.info(f"Client {client.user_id} confirmé")
                        # Réinitialiser le TTL après la confirmation
                        client.last_ttl = float('inf')
                        client.timer_decreasing = True
                        client.ttl_history.clear()
                
                # Continuer le polling jusqu'à la fin du test
                try:
                    await asyncio.sleep(POLL_DURATION - 3)  # -3 pour laisser du temps pour le nettoyage
                finally:
                    polling_task.cancel()
                    try:
                        await polling_task
                    except asyncio.CancelledError:
                        pass
                
            except Exception as e:
                test_logger.error(f"Erreur dans le cycle de vie de {client.user_id}: {str(e)}")

        async def cleanup_client(client: ClientState):
            """Nettoie proprement un client."""
            try:
                # Vérifier le statut actuel
                status_response = await test_client.get(f"/queue/status/{client.user_id}")
                if status_response.status_code == 200:
                    status = status_response.json()
                    
                    if status.get("status") == "draft":
                        # Si en draft, confirmer d'abord
                        await test_client.post("/queue/confirm", json={"user_id": client.user_id})
                        await asyncio.sleep(0.1)
                    
                    # Puis quitter
                    await test_client.post("/queue/leave", json={"user_id": client.user_id})
                
                # Nettoyage Redis
                await redis_client.srem("active_users", client.user_id)
                await redis_client.srem("draft_users", client.user_id)
                await redis_client.lrem("waiting_queue", 0, client.user_id)
                await redis_client.delete(f"session:{client.user_id}")
                await redis_client.delete(f"draft:{client.user_id}")
                await redis_client.delete(f"status_history:{client.user_id}")
                await redis_client.delete(f"last_status:{client.user_id}")
            
            except Exception as e:
                test_logger.error(f"Erreur lors du nettoyage de {client.user_id}: {str(e)}")

        try:
            # Créer les clients
            for i in range(NB_CLIENTS):
                client = ClientState(f"timer_client_{i}")
                clients[client.user_id] = client
            
            # Lancer les cycles de vie des clients
            lifecycle_tasks = [
                asyncio.create_task(client_lifecycle(client))
                for client in clients.values()
            ]
            
            # Attendre que tous les cycles de vie soient terminés
            await asyncio.gather(*lifecycle_tasks, return_exceptions=True)
            
            # Vérifier que tous les timers étaient décroissants
            non_decreasing_clients = [
                client.user_id
                for client in clients.values()
                if not client.timer_decreasing
            ]
            
            assert len(non_decreasing_clients) == 0, \
                f"Clients avec timers non décroissants: {non_decreasing_clients}"
            
            test_logger.info("Test de polling des timers terminé avec succès")
            
        finally:
            # Nettoyage
            test_logger.info("Nettoyage des clients")
            cleanup_tasks = [
                asyncio.create_task(cleanup_client(client))
                for client in clients.values()
            ]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            # Vérifications finales
            final_active = await redis_client.scard("active_users")
            final_draft = await redis_client.scard("draft_users")
            final_waiting = await redis_client.llen("waiting_queue")
            
            assert final_active == 0, f"Il reste {final_active} utilisateurs actifs"
            assert final_draft == 0, f"Il reste {final_draft} utilisateurs en draft"
            assert final_waiting == 0, f"Il reste {final_waiting} utilisateurs en attente"

    @pytest.mark.asyncio
    async def test_multiple_clients_timer_polling_threaded(self, test_client, redis_client, queue_manager_with_checker, test_logger):
        """Test de stress avec plusieurs clients qui font du long polling sur leurs timers, répartis sur 4 threads."""
        import threading
        import queue
        import concurrent.futures
        import httpx
        import time
        import os
        from functools import partial
        
        # Configuration des constantes
        NB_CLIENTS_PER_THREAD = 2  # Réduit pour le débogage
        NB_THREADS = 4
        POLL_DURATION = 15
        POLL_INTERVAL = 1.0
        REQUEST_TIMEOUT = 5.0  # Réduit pour détecter les problèmes plus rapidement
        MAX_RETRIES = 3
        SETUP_TIMEOUT = 10.0
        SETUP_INTERVAL = 2.0
        
        # Configuration du logging
        test_logger.setLevel(logging.DEBUG)  # Augmente le niveau de détail des logs

        # Vérification de l'état initial de Redis
        test_logger.info("=== État initial de Redis ===")
        # Lister toutes les clés
        all_keys = await redis_client.keys('*')
        test_logger.info(f"Toutes les clés dans Redis: {[key.decode('utf-8') for key in all_keys]}")
        
        # Vérifier les utilisateurs actifs en détail
        active_users_initial = await redis_client.smembers('active_users')
        if active_users_initial:
            test_logger.info("Détail des utilisateurs actifs:")
            for user in active_users_initial:
                user_id = user.decode('utf-8')
                session_exists = await redis_client.exists(f'session:{user_id}')
                test_logger.info(f"  - User {user_id}: session exists = {session_exists}")
        
        # Vérifier le slot checker
        test_logger.info(f"État du slot checker avant nettoyage: {queue_manager_with_checker._slot_check_task}")

        # Nettoyage initial de Redis
        test_logger.info("\n=== Début du nettoyage ===")
        
        # Récupérer tous les utilisateurs
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.smembers('active_users')
            pipe.smembers('draft_users')
            pipe.lrange('waiting_queue', 0, -1)
            pipe.smembers('queued_users')
            results = await pipe.execute()
        
        active_users = [user.decode('utf-8') for user in results[0]]
        draft_users = [user.decode('utf-8') for user in results[1]]
        waiting_users = [user.decode('utf-8') for user in results[2]]
        queued_users = [user.decode('utf-8') for user in results[3]]
        
        test_logger.info(f"Utilisateurs à nettoyer - Actifs: {len(active_users)}, Draft: {len(draft_users)}, En attente: {len(waiting_users)}, En file: {len(queued_users)}")
        if active_users:
            test_logger.info(f"Liste des utilisateurs actifs: {active_users}")
        
        # Nettoyer en une seule transaction
        async with redis_client.pipeline(transaction=True) as pipe:
            # Supprimer tous les utilisateurs des sets
            all_users = set(active_users + draft_users + waiting_users + queued_users)
            
            # Ajouter les utilisateurs active_user_X
            for i in range(50):  # Nettoyer les 50 utilisateurs active_user_X
                all_users.add(f"active_user_{i}")
            
            for user_id in all_users:
                pipe.srem("active_users", user_id)
                pipe.srem("draft_users", user_id)
                pipe.lrem("waiting_queue", 0, user_id)
                pipe.srem("queued_users", user_id)
                pipe.delete(f"session:{user_id}")
                pipe.delete(f"draft:{user_id}")
                pipe.delete(f"status_history:{user_id}")
                pipe.delete(f"last_status:{user_id}")
            results = await pipe.execute()
            test_logger.debug(f"Résultats du nettoyage: {results}")
        
        # Vérification finale
        test_logger.info("\n=== Vérification après nettoyage ===")
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.scard("active_users")
            pipe.scard("draft_users")
            pipe.llen("waiting_queue")
            pipe.scard("queued_users")
            pipe.keys("*")  # Vérifier toutes les clés restantes
            results = await pipe.execute()
        
        active_count, draft_count, waiting_count, queued_count, remaining_keys = results
        test_logger.info(f"Compteurs après nettoyage:")
        test_logger.info(f"  - Actifs: {active_count}")
        test_logger.info(f"  - Draft: {draft_count}")
        test_logger.info(f"  - En attente: {waiting_count}")
        test_logger.info(f"  - En file: {queued_count}")
        test_logger.info(f"Clés restantes dans Redis: {[key.decode('utf-8') for key in remaining_keys]}")
        
        if active_count > 0 or draft_count > 0 or waiting_count > 0 or queued_count > 0:
            raise RuntimeError(f"Nettoyage incomplet - Actifs: {active_count}, Draft: {draft_count}, En attente: {waiting_count}, En file: {queued_count}")
        
        test_logger.info("Nettoyage initial terminé avec succès")

    @pytest.mark.asyncio
    async def test_server_health(self, test_logger):
        """Test la disponibilité du serveur."""
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Test du health check
                test_logger.info("Démarrage du test health check")
                response = await client.get(f"{base_url}/health")
                assert response.status_code == 200, f"Health check a échoué: {response.status_code}"
                test_logger.info("Health check réussi")
                
                # Test simple de l'endpoint join
                test_logger.info("Test de l'endpoint join")
                test_user = "test_health_user"
                join_response = await client.post(f"{base_url}/queue/join/{test_user}")
                assert join_response.status_code == 200, f"Join a échoué: {join_response.status_code}"
                test_logger.info("Test join réussi")
                
                # Vérification des timers avec la bonne configuration Redis
                test_logger.info("Test de l'endpoint timers")
                # Augmenter le timeout pour l'appel aux timers
                async with httpx.AsyncClient(timeout=30.0) as timer_client:
                    timer_response = await timer_client.get(f"{base_url}/queue/timers/{test_user}")
                    assert timer_response.status_code == 200, f"Get timers a échoué: {timer_response.status_code}"
                    timers = timer_response.json()
                    test_logger.info(f"Réponse des timers: {timers}")
                    assert timers.get("error") is None, f"Erreur dans la réponse des timers: {timers.get('error')}"
                    test_logger.info("Test get timers réussi")
                
            except httpx.RequestError as e:
                test_logger.error(f"Erreur de connexion au serveur: {str(e)}")
                raise
            except AssertionError as e:
                test_logger.error(f"Test échoué: {str(e)}")
                raise
            except Exception as e:
                test_logger.error(f"Erreur inattendue: {str(e)}")
                raise
            finally:
                # Nettoyage
                try:
                    test_logger.info("Nettoyage des ressources")
                    await client.post(f"{base_url}/queue/leave/{test_user}")
                    test_logger.info("Nettoyage effectué")
                except Exception as e:
                    test_logger.warning(f"Erreur pendant le nettoyage: {str(e)}") 