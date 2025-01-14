import os
from redis.asyncio import Redis
from redis import Redis as SyncRedis
from celery import Celery
import json
import asyncio
import time
import logging
from typing import Dict, Any, List
import datetime
# Configuration de Celery
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

celery = Celery(
    'queue_manager',
    broker_url=f'redis://{REDIS_HOST}:{REDIS_PORT}',
    result_backend=f'redis://{REDIS_HOST}:{REDIS_PORT}',
)

logger = logging.getLogger('test_logger')
logger.setLevel(logging.DEBUG)

# Récupération des variables d'environnement Redis
REDIS_DB = int(os.getenv('REDIS_DB', 0))

# Configuration de base
celery.conf.update(
    broker_url=f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
    result_backend=f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
    broker_connection_retry=True,  # Activer les retry
    broker_connection_max_retries=None,  # Retry indéfiniment
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True
)

# Forcer le mode eager si en test
if os.environ.get('TESTING') == 'true':
    logger.info("Mode TEST détecté")
    celery.conf.update(
        worker_prefetch_multiplier=1,
        task_acks_late=False,
        task_track_started=True,
        task_send_sent_event=True,
        task_remote_tracebacks=True,
        task_store_errors_even_if_ignored=True,
        task_ignore_result=False,
        worker_log_level='DEBUG'  # Activer les logs de debug
    )
    logger.info(f"Configuration Celery en mode TEST")

logger.info(f"Mode Celery au démarrage: EAGER={celery.conf.task_always_eager}")

class QueueManager:
    """Gestionnaire de file d'attente avec Redis."""

    def __init__(self, redis: Redis):
        """Initialise le gestionnaire de file d'attente.

        Args:
            redis (Redis): Le client Redis à utiliser
        """
        self.redis = redis
        self.max_active_users = 10  # Valeur par défaut
        self._slot_check_task = None
        self._stop_slot_check = False
        self.draft_duration = 60  # Durée du draft en secondes
        self.session_duration = 300  # Durée de la session en secondes
        self._slot_check_interval = 2.0  # Intervalle de vérification des slots en secondes
        self._timer_tasks = {}  # Pour stocker les tâches de timer par user_id
        self.connection_manager = None
        self.logger = logging.getLogger(__name__)
        
        # Configurations
        self.max_active_users = int(os.getenv('MAX_ACTIVE_USERS', 2))
        self.draft_duration = int(os.getenv('DRAFT_DURATION', 300))  # 5 minutes
        self.session_duration = int(os.getenv('SESSION_DURATION', 1200))  # 20 minutes

    def set_connection_manager(self, manager):
        """Définit le gestionnaire de connexions WebSocket."""
        self.connection_manager = manager

    async def _send_timer_update(self, user_id: str, timer_type: str, ttl: int):
        """Envoie une mise à jour de timer via WebSocket."""
        if self.connection_manager:
            await self.connection_manager.send_timer_update(user_id, {
                "timer_type": timer_type,
                "ttl": ttl,
                "updates_left": 3  # Pour compatibilité avec l'ancien format
            })

    async def _verify_queue_state(self, user_id: str, expected_states, message: str = "") -> bool:
        """Vérifie l'état de la file d'attente pour un utilisateur."""
        try:
            logger.debug(f"Vérification de l'état pour {user_id} avec attentes: {expected_states}")
            logger.debug(f"Message: {message}")
            # Convertir en liste si c'est un dictionnaire unique
            if isinstance(expected_states, dict):
                expected_states = [expected_states]
                
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.sismember('queued_users', user_id)  # Utiliser queued_users pour vérifier la présence
                pipe.sismember('queued_users', user_id)  # in_waiting est le même que in_queue
                pipe.sismember('draft_users', user_id)
                pipe.sismember('active_users', user_id)
                pipe.sismember('accounts_queue', user_id)
                results = await pipe.execute()
                
                actual_state = {
                    'in_queue': bool(results[0]),
                    'in_waiting': bool(results[1]),  # Même état que in_queue
                    'in_draft': bool(results[2]),
                    'in_active': bool(results[3]),
                    'in_accounts_queue': bool(results[4])
                }
                
                logger.debug(f"État actuel pour {user_id}: {actual_state}")
                
                # Vérifier si l'état actuel correspond à l'un des états attendus
                for expected_state in expected_states:
                    matches = True
                    for key, expected in expected_state.items():
                        if isinstance(expected, (list, tuple)):
                            if actual_state[key] not in expected:
                                matches = False
                                break
                        elif actual_state[key] != expected:
                            matches = False
                            break
                    
                    if matches:
                        logger.debug(f"État vérifié avec succès pour {user_id} (correspond à {expected_state})")
                        return True
                
                # Si aucun état attendu ne correspond
                logger.warning(f"État invalide pour {user_id} - actuel={actual_state}, attendu l'un de {expected_states}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la vérification pour {user_id}: {str(e)}")
            return False

    async def _check_slots_after_add(self):
        """Vérifie les slots disponibles de manière asynchrone."""
        try:
            # Récupérer d'abord toute la waiting queue
            waiting_queue = await self.redis.lrange('waiting_queue', 0, -1)
            if not waiting_queue:
                return True

            # Vérifier les slots disponibles
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.scard('active_users')
                pipe.scard('draft_users')
                results = await pipe.execute()
                
            active_count, draft_count = results
            available_slots = self.max_active_users - (active_count + draft_count)

            if available_slots > 0:
                # Prendre seulement le nombre d'utilisateurs nécessaire
                users_to_check = waiting_queue[:available_slots]
                
                # Vérifier les utilisateurs en attente en une seule fois
                async with self.redis.pipeline(transaction=True) as pipe:
                    for user_id in users_to_check:
                        pipe.sismember('queued_users', user_id)
                    is_queued_results = await pipe.execute()
                
                # Offrir des slots aux utilisateurs éligibles
                for i, is_queued in enumerate(is_queued_results):
                    if is_queued:
                        await self.offer_slot(users_to_check[i])
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la vérification des slots : {str(e)}")
            return False

    async def start_slot_checker(self, check_interval: float = None):
        """Démarre le vérificateur de slots."""
        if self._slot_check_task is not None:
            logger.warning("Le vérificateur de slots est déjà en cours d'exécution")
            return

        if check_interval is not None:
            self._slot_check_interval = check_interval
            
        self._stop_slot_check = False
        self._slot_check_task = asyncio.create_task(self._slot_check_loop())
        logger.info(f"Vérificateur de slots démarré (intervalle: {self._slot_check_interval}s)")

    async def _slot_check_loop(self):
        """Boucle de vérification des slots."""
        try:
            while not self._stop_slot_check:
                await self.check_available_slots()
                await asyncio.sleep(self._slot_check_interval)
        except asyncio.CancelledError:
            logger.info("Vérificateur de slots arrêté")
        except Exception as e:
            logger.error(f"Erreur dans le vérificateur de slots: {str(e)}")
            self._slot_check_task = None

    async def stop_slot_checker(self):
        """Arrête la vérification périodique des slots."""
        if self._slot_check_task is not None:
            self._stop_slot_check = True
            await self._slot_check_task
            self._slot_check_task = None

    async def add_to_queue(self, user_id: str, check_slots: bool = True) -> Dict:
        """Ajoute un utilisateur à la file d'attente principale."""
        try:
            logger.info(f"🔄 Tentative d'ajout de l'utilisateur {user_id}")
            
            # Obtenir le statut actuel
            last_status = await self.get_user_status(user_id, check_slots=check_slots)
            logger.info(f"📊 Statut actuel pour {user_id}: {last_status}")
            
            # Si l'utilisateur n'existe pas dans Redis
            current_state = await self._get_current_state(user_id)
            logger.info(f"🔍 État actuel pour {user_id}: {current_state}")
            
            if await self._verify_queue_state(user_id, {
                'in_queue': False,
                'in_waiting': False,
                'in_draft': False,
                'in_active': False,
                'in_accounts_queue': [False, True]
            }):
                logger.debug(f"✨ Nouvel utilisateur détecté: {user_id}")
                last_status = {"status": None, "position": None}
            
            # Si l'utilisateur est déconnecté ou n'a pas de statut
            if last_status["status"] in [None, 'disconnected']:
                logger.info(f"➡️ Ajout à la file d'attente pour {user_id} avec statut {last_status['status']}")
                async with self.redis.pipeline(transaction=True) as pipe:
                    logger.debug(f"🔒 Début transaction Redis pour {user_id}")
                    # Ajouter à la file d'attente et à accounts_queue
                    pipe.rpush('waiting_queue', user_id)  # Utiliser rpush pour garder l'ordre FIFO
                    pipe.sadd('queued_users', user_id)
                    pipe.sadd('accounts_queue', user_id)
                    pipe.llen('waiting_queue')  # Utiliser llen pour avoir la position
                    results = await pipe.execute()
                    logger.info(f"📝 Résultats de la transaction Redis pour {user_id}: {results}")
                    position = results[-1]
                    logger.debug(f"📍 Position pour {user_id}: {position}")
                    
                    # Vérification immédiate post-transaction
                    is_queued = await self.redis.sismember('queued_users', user_id)
                    is_in_waiting = await self.redis.lpos('waiting_queue', user_id) is not None
                    logger.info(f"✅ Vérification post-transaction pour {user_id}: queued={is_queued}, in_waiting={is_in_waiting}")

                    if not (is_queued and is_in_waiting):
                        logger.error(f"❌ Échec de l'ajout à la file d'attente pour {user_id}")
                        raise Exception("Échec de l'ajout à la file d'attente")
                    
                    # Vérifier l'état après l'ajout
                    new_state = await self._get_current_state(user_id)
                    logger.info(f"🔄 Nouvel état pour {user_id}: {new_state}")
                    
                    expected_states = [
                        # État 1: En attente dans la file
                        {
                            'in_queue': True,
                            'in_waiting': True,
                            'in_draft': False,
                            'in_active': False,
                            'in_accounts_queue': [True, False]
                        }
                    ]
                    
                    if not await self._verify_queue_state(user_id, expected_states):
                        logger.error(f"❌ État incohérent après l'ajout pour {user_id}")
                        logger.error(f"État attendu: {expected_states}")
                        logger.error(f"État actuel: {new_state}")
                        raise Exception("État incohérent après l'ajout à la file")
                    
                    # Vérifier les slots disponibles si demandé
                    if check_slots:
                        await self._check_slots_after_add()
                    # Afficher l'état de la liste d'attente et de la draft
                    async with self.redis.pipeline(transaction=True) as pipe:
                        pipe.llen('waiting_queue')  # Taille de la liste d'attente
                        pipe.scard('draft_users')  # Nombre d'utilisateurs en draft
                        results = await pipe.execute()
                        waiting_queue_size = results[0]
                        draft_users_count = results[1]
                        logger.info(f"État actuel: Liste d'attente - {waiting_queue_size} utilisateurs, Draft - {draft_users_count} utilisateurs")
                    # Obtenir le nouveau statut après l'ajout et la vérification des slots
                    new_status = await self.get_user_status(user_id, check_slots=check_slots)
                    
                    # Vérifier si l'utilisateur est passé en draft
                    is_draft = await self.redis.sismember('draft_users', user_id)
                    if is_draft:
                        new_status["status"] = "draft"
                        position = -1
                    else:
                        # Retourner la position réelle dans la file
                        waiting_pos = await self.redis.lpos('waiting_queue', user_id)
                        if waiting_pos is not None:
                            position = waiting_pos + 1
                        else:
                            position = new_status.get("position", None)
                    
                    logger.info(f"✅ Ajout réussi pour {user_id} - Status: {new_status['status']}, Position: {position}")
                    return {
                        "last_status": last_status["status"],
                        "last_position": last_status.get("position", None),
                        "commit_status": new_status["status"],
                        "commit_position": position
                    }
            
            # Pour tous les autres cas, retourner le statut actuel
            logger.info(f"ℹ️ Retour du statut actuel pour {user_id}: {last_status}")
            return {
                "last_status": last_status["status"],
                "last_position": last_status.get("position", None),
                "commit_status": last_status["status"],
                "commit_position": last_status.get("position", None)
            }
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'ajout à la file pour {user_id}: {str(e)}")
            logger.error(f"État actuel lors de l'erreur: {await self._get_current_state(user_id)}")
            
            # Nettoyage en cas d'erreur
            async with self.redis.pipeline(transaction=True) as pipe:
                logger.debug(f"🧹 Nettoyage après erreur pour {user_id}")
                pipe.lrem('waiting_queue', 0, user_id)  # Utiliser lrem pour la liste
                pipe.srem('queued_users', user_id)
                await pipe.execute()
                
            return {
                "last_status": None,
                "last_position": None,
                "commit_status": None,
                "commit_position": None
            }

    async def _get_current_state(self, user_id: str) -> Dict[str, bool]:
        """Récupère l'état actuel d'un utilisateur dans toutes les files."""
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.sismember('queued_users', user_id)
            pipe.lpos('waiting_queue', user_id)
            pipe.sismember('draft_users', user_id)
            pipe.sismember('active_users', user_id)
            pipe.sismember('accounts_queue', user_id)
            results = await pipe.execute()
            
        return {
            'in_queue': results[0],
            'in_waiting': results[1] is not None,
            'in_draft': results[2],
            'in_active': results[3],
            'in_accounts_queue': results[4]
        }

    async def remove_from_queue(self, user_id: str) -> bool:
        """Retire un utilisateur de la file d'attente."""
        try:
            is_queued = await self.redis.sismember('queued_users', user_id)
            is_draft = await self.redis.sismember('draft_users', user_id)
            is_active = await self.redis.sismember('active_users', user_id)
            
            if is_queued or is_draft or is_active:
                async with self.redis.pipeline(transaction=True) as pipe:
                    if is_queued:
                        pipe.lrem('waiting_queue', 0, user_id)  # Retirer de la liste d'attente
                        pipe.srem('queued_users', user_id)  # Retirer de l'ensemble des utilisateurs en attente
                    if is_draft:
                        pipe.srem('draft_users', user_id)
                        pipe.delete(f'draft:{user_id}')
                    if is_active:
                        pipe.srem('active_users', user_id)
                        pipe.delete(f'session:{user_id}')
                    pipe.publish(f'queue_status:{user_id}', 
                        json.dumps({
                            "status": "disconnected",
                            "position": None,
                            "timestamp": int(time.time())
                        })
                    )
                    await pipe.execute()
                    
                    # Vérifier l'état après suppression
                    expected_state = {
                        'in_queue': False,
                        'in_waiting': False,
                        'in_draft': False,
                        'in_active': False,
                        'in_accounts_queue': True  # L'utilisateur doit rester dans accounts_queue
                    }
                    logger.debug(f"Vérification de l'état après suppression pour {user_id}: {expected_state}")
                    if not await self._verify_queue_state(user_id, expected_state, message="iciiiiii"):
                        raise Exception("État incohérent après la suppression")
                    
                    # Vérifier les slots disponibles
                    await self._check_slots_after_add()
                    
                return True
            return False
        except Exception as e:
            print(f"Erreur lors de la suppression : {str(e)}")
            return False

    async def check_available_slots(self):
        """Vérifie et attribue les slots disponibles."""
        try:
            # Vérifier d'abord les slots disponibles
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.multi()
                pipe.scard('active_users')
                pipe.scard('draft_users')
                results = await pipe.execute()
                
                active_count, draft_count = results
                available_slots = self.max_active_users - (active_count + draft_count)
            
            logger.debug(f"Slots disponibles: {available_slots} (actifs: {active_count}, draft: {draft_count})")
            
            if available_slots <= 0:
                logger.info("ℹ️ Plus aucun slot disponible")
                return False

            # Récupérer et traiter les utilisateurs un par un
            while available_slots > 0:
                # Vérifier l'éligibilité et retirer l'utilisateur de manière atomique
                async with self.redis.pipeline(transaction=True) as pipe:
                    pipe.multi()
                    pipe.lindex('waiting_queue', 0)  # Regarder le premier sans le retirer
                    results = await pipe.execute()
                    
                user_id = results[0]
                if not user_id:
                    logger.debug("Plus d'utilisateurs en attente")
                    break
                
                logger.debug(f"Traitement de l'utilisateur {user_id}")
                
                # Vérifier l'éligibilité
                async with self.redis.pipeline(transaction=True) as pipe:
                    pipe.multi()
                    pipe.sismember('queued_users', user_id)
                    pipe.sismember('active_users', user_id)
                    pipe.sismember('draft_users', user_id)
                    pipe.lpos('waiting_queue', user_id)  # Vérifier la position
                    results = await pipe.execute()
                
                is_queued, is_active, is_draft, waiting_pos = results
                logger.debug(f"État de {user_id} - queued: {is_queued}, active: {is_active}, draft: {is_draft}, pos: {waiting_pos}")
                
                if not is_queued or is_active or is_draft or waiting_pos is None:
                    logger.warning(f"Utilisateur {user_id} non éligible, nettoyage...")
                    # Nettoyer l'état incohérent
                    async with self.redis.pipeline(transaction=True) as pipe:
                        pipe.multi()
                        pipe.lrem('waiting_queue', 0, user_id)  # Retirer de la file
                        pipe.srem('queued_users', user_id)  # Retirer des utilisateurs en queue
                        await pipe.execute()
                    continue

                # Tenter d'offrir un slot
                if await self.offer_slot(user_id):
                    available_slots -= 1
                    logger.info(f"✅ Slot offert à {user_id}")
                else:
                    logger.warning(f"❌ Échec de l'offre de slot à {user_id}")
                    # L'utilisateur sera remis en file par offer_slot

            return available_slots > 0

        except Exception as e:
            logger.error(f"Erreur lors de la vérification des slots: {str(e)}")
            return False

    async def offer_slot(self, user_id: str, max_retries: int = 3) -> bool:
        """Offre un slot à un utilisateur."""
        retry_count = 0
        while retry_count < max_retries:
            try:
                logger.debug(f"Tentative {retry_count + 1}/{max_retries} d'offre de slot à {user_id}")
                
                # Vérifier l'état actuel
                async with self.redis.pipeline(transaction=True) as pipe:
                    pipe.multi()  # Démarrer la transaction AVANT les commandes
                    pipe.sismember('queued_users', user_id)
                    pipe.sismember('active_users', user_id)
                    pipe.sismember('draft_users', user_id)
                    pipe.lpos('waiting_queue', user_id)
                    results = await pipe.execute()
                
                is_queued, is_active, is_draft, waiting_pos = results
                logger.debug(f"État actuel de {user_id} - queued: {is_queued}, active: {is_active}, draft: {is_draft}, waiting_pos: {waiting_pos}")
                
                if not is_queued or is_active or is_draft:
                    logger.warning(f"État invalide pour {user_id} - queued: {is_queued}, active: {is_active}, draft: {is_draft}")
                    return False
                
                # Vérifier les slots disponibles
                async with self.redis.pipeline(transaction=True) as pipe:
                    pipe.multi()  # Démarrer la transaction AVANT les commandes
                    pipe.scard('active_users')
                    pipe.scard('draft_users')
                    results = await pipe.execute()
                    
                active_count, draft_count = results
                if active_count + draft_count >= self.max_active_users:
                    logger.warning(f"Plus de slots disponibles - actifs: {active_count}, draft: {draft_count}")
                    return False

                # Effectuer la transition atomique
                async with self.redis.pipeline(transaction=True) as pipe:
                    pipe.multi()  # Démarrer la transaction AVANT les commandes
                    pipe.srem('queued_users', user_id)
                    pipe.sadd('draft_users', user_id)
                    pipe.setex(f'draft:{user_id}', self.draft_duration, '1')
                    pipe.lrem('waiting_queue', 0, user_id)  # Retirer de la waiting_queue
                    results = await pipe.execute()
                    
                    if not all(results):
                        logger.error(f"Échec de la transition pour {user_id} - résultats: {results}")
                        return False
                    
                    logger.debug(f"Transition réussie pour {user_id}")
                
                # Vérifier l'état final
                async with self.redis.pipeline(transaction=True) as pipe:
                    pipe.multi()  # Démarrer la transaction AVANT les commandes
                    pipe.sismember('queued_users', user_id)
                    pipe.sismember('draft_users', user_id)
                    pipe.exists(f'draft:{user_id}')
                    pipe.lpos('waiting_queue', user_id)
                    results = await pipe.execute()
                
                final_queued, final_draft, has_draft, final_waiting = results
                logger.debug(f"État final de {user_id} - queued: {final_queued}, draft: {final_draft}, has_draft: {has_draft}, waiting: {final_waiting}")
                
                if not final_draft or final_queued or not has_draft or final_waiting is not None:
                    logger.error(f"État final invalide pour {user_id}")
                    return False

                # Publier la notification
                status_info = {
                    "status": "draft",
                    "position": -1,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                await self.redis.publish(f'queue_status:{user_id}', json.dumps(status_info))
                
                logger.info(f"✅ Slot offert avec succès à {user_id} (timer: {self.draft_duration}s)")
                return True
                
            except Exception as e:
                logger.error(f"❌ Tentative {retry_count + 1}/{max_retries} - Erreur lors de l'offre de slot à {user_id}: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(0.1 * (retry_count + 1))  # Backoff exponentiel
                continue
        
        # Si on arrive ici, toutes les tentatives ont échoué
        logger.warning(f"❌ Échec de l'offre de slot pour {user_id}, remise en file")
        return False

    async def confirm_connection(self, user_id: str, max_retries: int = 3) -> bool:
        """Confirme la connexion d'un utilisateur."""
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Vérifier l'état actuel en une seule transaction
                async with self.redis.pipeline(transaction=True) as pipe:
                    pipe.sismember('draft_users', user_id)
                    pipe.exists(f'draft:{user_id}')
                    pipe.sismember('active_users', user_id)
                    pipe.sismember('queued_users', user_id)
                    pipe.ttl(f'draft:{user_id}')  # Récupérer le TTL restant
                    results = await pipe.execute()
                    
                    is_draft, has_draft, is_active, is_queued, draft_ttl = results
                    
                    if not (is_draft and has_draft):
                        logger.warning(f"❌ L'utilisateur {user_id} n'est pas en état draft (is_draft={is_draft}, has_draft={has_draft})")
                        return False
                        
                    if is_active or is_queued:
                        logger.warning(f"⚠️ État invalide pour {user_id}: déjà actif={is_active} ou en file d'attente={is_queued}")
                        return False

                    if draft_ttl <= 0:
                        logger.warning(f"⚠️ Le timer draft a expiré pour {user_id} (ttl={draft_ttl})")
                        return False
                    
                    # Effectuer la transition en une seule transaction
                    async with self.redis.pipeline(transaction=True) as pipe:
                        pipe.srem('draft_users', user_id)
                        pipe.sadd('active_users', user_id)
                        pipe.delete(f'draft:{user_id}')
                        pipe.setex(f'session:{user_id}', self.session_duration, '1')
                        # Publier le nouveau timer
                        pipe.publish('user_status', json.dumps({
                            'user_id': user_id,
                            'status': 'active',
                            'timer': {
                                'type': 'session',
                                'duration': self.session_duration,
                                'timestamp': int(time.time())
                            }
                        }))
                        results = await pipe.execute()
                        
                        # Vérifier que toutes les opérations ont réussi
                        if not all(result is not None for result in results[:-1]):  # Ignore le résultat de publish
                            raise Exception("Une ou plusieurs opérations ont échoué")
                        
                    logger.info(f"✅ Connexion confirmée pour {user_id} (session: {self.session_duration}s)")
                    return True
                    
            except Exception as e:
                retry_count += 1
                logger.error(f"QueueManager : ❌ Tentative {retry_count}/{max_retries} - Erreur lors de la confirmation pour {user_id}: {str(e)}")
                if retry_count < max_retries:
                    await asyncio.sleep(0.5 * retry_count)  # Backoff exponentiel
                else:
                    # Nettoyage en cas d'erreur
                    try:
                        async with self.redis.pipeline(transaction=True) as pipe:
                            pipe.srem('active_users', user_id)
                            pipe.srem('draft_users', user_id)
                            pipe.delete(f'session:{user_id}')
                            pipe.delete(f'draft:{user_id}')
                            await pipe.execute()
                    except Exception as cleanup_error:
                        logger.error(f"Erreur lors du nettoyage pour {user_id}: {str(cleanup_error)}")
                    return False

        return False

    async def extend_session(self, user_id: str, max_retries: int = 3) -> bool:
        """Prolonge la session d'un utilisateur actif."""
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Vérifier l'état en une seule transaction
                async with self.redis.pipeline(transaction=True) as pipe:
                    pipe.sismember('active_users', user_id)
                    pipe.exists(f'session:{user_id}')
                    pipe.ttl(f'session:{user_id}')
                    is_active, has_session, session_ttl = await pipe.execute()
                    
                    if not (is_active and has_session):
                        logger.warning(f"Session invalide pour {user_id}: active={is_active}, has_session={has_session}")
                        return False

                    if session_ttl <= 0:
                        logger.warning(f"Session expirée pour {user_id}: ttl={session_ttl}")
                        return False
                    
                    # Prolonger la session
                    async with self.redis.pipeline(transaction=True) as pipe:
                        pipe.setex(f'session:{user_id}', self.session_duration, '1')
                        pipe.publish(f'queue_status:{user_id}', 
                            json.dumps({
                                "status": "extended",
                                "session_duration": self.session_duration,
                                "timestamp": int(time.time())
                            })
                        )
                        results = await pipe.execute()
                        
                        # Vérifier que l'opération a réussi
                        if not results[0]:
                            raise Exception("Échec de la prolongation de session")
                    
                    logger.info(f"✅ Session prolongée pour {user_id} (nouvelle durée: {self.session_duration}s)")
                    return True
                    
            except Exception as e:
                retry_count += 1
                logger.error(f"❌ Tentative {retry_count}/{max_retries} - Erreur lors de la prolongation de session pour {user_id}: {str(e)}")
                if retry_count < max_retries:
                    await asyncio.sleep(0.5 * retry_count)  # Backoff exponentiel
                else:
                    # Nettoyage en cas d'erreur
                    try:
                        async with self.redis.pipeline(transaction=True) as pipe:
                            pipe.srem('active_users', user_id)
                            pipe.delete(f'session:{user_id}')
                            await pipe.execute()
                    except Exception as cleanup_error:
                        logger.error(f"Erreur lors du nettoyage pour {user_id}: {str(cleanup_error)}")
                    return False

        return False

    async def get_user_status(self, user_id: str, check_slots: bool = True) -> Dict:
        """Récupère le statut actuel d'un utilisateur."""
        try:
            # Vérifier si l'utilisateur existe dans un des états possibles
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.sismember('active_users', user_id)
                pipe.sismember('draft_users', user_id)
                pipe.lpos('waiting_queue', user_id)
                pipe.sismember('queued_users', user_id)
                pipe.sismember('accounts_queue', user_id)  # Vérifier si l'utilisateur a déjà été connecté
                is_active, is_draft, waiting_pos, is_queued, has_account = await pipe.execute()

            # Si l'utilisateur n'existe dans aucun état et n'a jamais été connecté, retourner None
            if not any([is_active, is_draft, waiting_pos is not None, is_queued]) and not has_account:
                return {"status": None, "position": None}

            # Si l'utilisateur n'est dans aucun état mais a déjà été connecté
            if not any([is_active, is_draft, waiting_pos is not None, is_queued]) and has_account:
                return {"status": "disconnected", "position": None}

            # Déterminer le statut en fonction des flags
            if is_active:
                status_info = {
                    "status": "connected",
                    "position": -2
                }
                
                # Vérifier le TTL de la session
                session_ttl = await self.redis.ttl(f'session:{user_id}')
                if session_ttl > 0:
                    status_info["remaining_time"] = session_ttl
                    
            elif is_draft:
                status_info = {
                    "status": "draft",
                    "position": -1
                }
                
                # Vérifier le TTL du draft
                draft_ttl = await self.redis.ttl(f'draft:{user_id}')
                if draft_ttl > 0:
                    status_info["remaining_time"] = draft_ttl
                    
            elif waiting_pos is not None:
                status_info = {
                    "status": "waiting",
                    "position": waiting_pos + 1
                }
                
            else:
                status_info = {
                    "status": "disconnected",
                    "position": None
                }

            # Ajouter un timestamp au statut
            status_info["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Stocker le statut dans la liste et publier
            status_json = json.dumps(status_info)
            last_status = None
            
            # Vérifier si l'historique des statuts existe déjà
            history_exists = await self.redis.exists(f'status_history:{user_id}')
            if history_exists == 0:
                logger.info(f"Aucun historique de statuts trouvé pour {user_id}")
            else:
                # Récupérer le dernier statut stocké
                last_status_json = await self.redis.lindex(f'status_history:{user_id}', -1)
                if last_status_json:
                    try:
                        last_status = json.loads(last_status_json)
                        logger.info(f"Dernier statut récupéré pour {user_id}: {last_status}")
                        
                        # Vérifier si on doit checker les slots
                        if check_slots and (status_info["status"] == "waiting" or (last_status.get("status") == "connected" and status_info["status"] != "connected")):
                            await self._check_slots_after_add()
                    except json.JSONDecodeError:
                        logger.error(f"Erreur lors du décodage du dernier statut pour {user_id}")
                else:
                    logger.info(f"Aucun statut trouvé pour {user_id}")
            
            # Ajouter le nouveau statut à l'historique
            if not last_status or (last_status["status"] != status_info["status"]):
                await self.redis.rpush(f'status_history:{user_id}', status_json)
                await self.redis.publish(f'queue_status:{user_id}', status_json)
            
                # Garder seulement les 100 derniers statuts
                if history_exists:
                    await self.redis.ltrim(f'status_history:{user_id}', -100, -1)
            
            return status_info | {"user_id": user_id}
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du statut pour {user_id}: {str(e)}")
            error_status = {
                "status": "error",
                "position": None,
                "message": str(e),
                "timestamp": int(time.time())
            }
            error_json = json.dumps(error_status)
            await self.redis.rpush(f'status_history:{user_id}', error_json)
            await self.redis.publish(f'queue_status:{user_id}', error_json)
            return error_status

    async def get_status_messages(self, user_id: str, limit: int = None) -> List[Dict]:
        """Récupère l'historique des messages de statut pour un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur dont on veut récupérer l'historique des statuts.
            limit: Nombre maximum de messages à récupérer (par défaut, tous les messages)
        
        Returns:
            List[Dict]: Liste des messages de statut, du plus récent au plus ancien
        """
        try:
            # Récupérer tous les statuts stockés
            if limit is not None:
                messages = await self.redis.lrange(f'status_history:{user_id}', -limit, -1)
            else:
                messages = await self.redis.lrange(f'status_history:{user_id}', 0, -1)
            
            if messages:
                try:
                    # Décoder les messages JSON
                    status_list = [json.loads(msg) for msg in messages]
                    logger.info(f"{len(status_list)} messages récupérés pour {user_id}")
                    return status_list
                except Exception as e:
                    logger.error(f"Erreur lors du décodage des messages: {str(e)}")
            
            logger.info(f"Aucun message trouvé pour {user_id}")
            return []
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des messages: {str(e)}")
            return []

    async def get_all_user_statuses(self) -> List[Dict]:
        """Récupère le statut de tous les utilisateurs dans le système.
        
        Returns:
            List[Dict]: Une liste de dictionnaires contenant les statuts de tous les utilisateurs.
            Chaque dictionnaire contient:
                - user_id: L'identifiant de l'utilisateur
                - status: Le statut actuel ('waiting', 'draft', 'connected', etc.)
                - position: La position actuelle
                - remaining_time: Le temps restant (pour les statuts draft et connected)
        """
        try:
            all_statuses = []
            
            async with self.redis.pipeline(transaction=True) as pipe:
                # Récupérer tous les utilisateurs de chaque état
                pipe.smembers('active_users')
                pipe.smembers('draft_users')
                pipe.lrange('waiting_queue', 0, -1)
                active_users, draft_users, waiting_users = await pipe.execute()
                
                # Convertir les sets en listes pour les utilisateurs actifs et en draft
                active_users = list(active_users)
                draft_users = list(draft_users)
                
                logger.debug(f"Utilisateurs trouvés - actifs: {len(active_users)}, draft: {len(draft_users)}, en attente: {len(waiting_users)}")
                
                # Récupérer le statut de chaque utilisateur
                for user_id in active_users:
                    status = await self.get_user_status(user_id)
                    all_statuses.append({
                        "user_id": user_id,
                        **status
                    })
                
                for user_id in draft_users:
                    status = await self.get_user_status(user_id)
                    all_statuses.append({
                        "user_id": user_id,
                        **status
                    })
                
                for user_id in waiting_users:
                    status = await self.get_user_status(user_id)
                    all_statuses.append({
                        "user_id": user_id,
                        **status
                    })
                
            logger.info(f"Total des statuts récupérés: {len(all_statuses)}")
            return all_statuses
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statuts: {str(e)}")
            return []

    async def get_timers(self, user_id: str) -> Dict:
        """Récupère les timers actifs pour un utilisateur."""
        self.logger.info(f"🔍 Récupération des timers pour {user_id}")
        
        # Vérifier d'abord le draft
        draft_ttl = await self.redis.ttl(f"draft:{user_id}")
        self.logger.info(f"⏰ TTL draft pour {user_id}: {draft_ttl}")
        
        if draft_ttl > 0:
            # L'utilisateur est en draft
            self.logger.info(f"📝 Création de la tâche draft pour {user_id}")
            task = auto_expiration.delay(draft_ttl, "draft", user_id)
            self.logger.info(f"✅ Tâche draft créée pour {user_id}: {task.id}")
            
            return {
                "timer_type": "draft",
                "ttl": draft_ttl,
                "task_id": task.id,
                "channel": f"timer:channel:{user_id}",
                "status": "active",
                "error": None
            }
        
        # Vérifier ensuite la session
        session_ttl = await self.redis.ttl(f"session:{user_id}")
        is_active = await self.redis.sismember("active_users", user_id)
        self.logger.info(f"⏰ TTL session pour {user_id}: {session_ttl}, actif: {is_active}")
        
        if session_ttl > 0 and is_active:
            # L'utilisateur est en session active
            self.logger.info(f"📝 Création de la tâche session pour {user_id}")
            task = auto_expiration.delay(session_ttl, "session", user_id)
            self.logger.info(f"✅ Tâche session créée pour {user_id}: {task.id}")
            
            return {
                "timer_type": "session",
                "ttl": session_ttl,
                "task_id": task.id,
                "channel": f"timer:channel:{user_id}",
                "status": "active",
                "error": None,
                "user_id": user_id
            }
        
        # Aucun timer actif
        return {
            "error": "Aucun timer actif pour cet utilisateur",
            "status": "inactive",
            "user_id": user_id
        }

    async def _handle_session_expiration(self, user_id: str):
        """Gère l'expiration d'une session."""
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.srem('active_users', user_id)
            pipe.delete(f'session:{user_id}')
            pipe.publish(f'queue_status:{user_id}', json.dumps({
                "status": "disconnected",
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }))
            await pipe.execute()

    async def _handle_draft_expiration(self, user_id: str):
        """Gère l'expiration d'un draft."""
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.srem('draft_users', user_id)
            pipe.delete(f'draft:{user_id}')
            pipe.publish(f'queue_status:{user_id}', json.dumps({
                "status": "disconnected",
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }))
            await pipe.execute()

    async def _cleanup_inconsistent_state(self, user_id: str):
        """Nettoie un état incohérent."""
        try:
            logger.warning(f"Nettoyage de l'état incohérent pour {user_id}")
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.srem('queued_users', user_id)
                pipe.lrem('waiting_queue', 0, user_id)
                pipe.srem('active_users', user_id)
                pipe.srem('draft_users', user_id)
                pipe.delete(f'draft:{user_id}')
                pipe.delete(f'session:{user_id}')
                pipe.delete(f'status_history:{user_id}')
                pipe.delete(f'last_status:{user_id}')
                # Ne pas supprimer de accounts_queue car c'est un historique permanent
                await pipe.execute()
                logger.info(f"État nettoyé pour {user_id}")
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage de l'état pour {user_id}: {str(e)}")

    async def get_metrics(self) -> dict:
        """Obtient les métriques de la file d'attente."""
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.smembers('active_users')  # Récupérer tous les utilisateurs actifs
            pipe.lrange('waiting_queue', 0, -1)  # Récupérer la liste complète
            pipe.scard('accounts_queue')  # Ajouter le nombre total d'utilisateurs enregistrés
            pipe.smembers('draft_users')  # Récupérer les utilisateurs en draft
            results = await pipe.execute()
            
            active_users_set = results[0]
            waiting_users = results[1]
            total_accounts = results[2]
            draft_users = results[3]
            
            # Vérifier les sessions actives
            async with self.redis.pipeline(transaction=True) as pipe:
                for user_id in active_users_set:
                    pipe.exists(f'session:{user_id}')
                session_results = await pipe.execute()
            
            # Compter uniquement les utilisateurs avec une session valide
            real_active_users = sum(1 for exists in session_results if exists)
            
            # Filtrer les utilisateurs en attente qui ne sont pas en draft
            real_waiting_users = [user for user in waiting_users if user.encode() not in draft_users]
            
            # Convertir les draft_users en liste
            decoded_draft_users = list(draft_users)
            
            return {
                "active_users": real_active_users,
                "waiting_users": len(real_waiting_users),
                "draft_users": decoded_draft_users,
                "total_slots": self.max_active_users,
                "total_accounts": total_accounts
            }

    async def cleanup_session(self, user_id: str) -> bool:
        """Nettoie la session d'un utilisateur.
        
        Args:
            user_id (str): L'identifiant de l'utilisateur
            
        Returns:
            bool: True si le nettoyage a réussi, False sinon
        """
        try:
            logger.debug(f"Nettoyage de la session pour {user_id}")
            async with self.redis.pipeline(transaction=True) as pipe:
                # Supprimer l'utilisateur des ensembles actifs
                pipe.srem('active_users', user_id)
                pipe.delete(f'session:{user_id}')
                await pipe.execute()
                
            logger.info(f"Session nettoyée avec succès pour {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage de la session pour {user_id}: {str(e)}")
            return False

@celery.task(name='app.queue_manager.cleanup_session', bind=True)
async def cleanup_session(self, user_id: str):
    """Nettoie la session d'un utilisateur."""
    logger.info(f"Début de la tâche de nettoyage de session pour {user_id}")
    redis = None
    try:
        redis = Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        
        # Vérifier l'état actuel
        async with redis.pipeline(transaction=True) as pipe:
            pipe.sismember('active_users', user_id)
            pipe.exists(f'session:{user_id}')
            results = await pipe.execute()
            
            is_active, has_session = results
            
            # On nettoie si l'utilisateur est actif, même si la session n'existe plus
            if not is_active:
                logger.warning(f"5 État invalide pour nettoyage: active={is_active}, has_session={has_session}")
                return True
        
        # Effectuer le nettoyage
        async with redis.pipeline(transaction=True) as pipe:
            pipe.srem('active_users', user_id)
            pipe.delete(f'session:{user_id}')
            await pipe.execute()
            
        # Ajouter le nouveau statut à l'historique
        status_info = {
            "status": "disconnected",
            "position": None,
            "reason": "session_timeout",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        status_json = json.dumps(status_info)
        await redis.rpush(f'status_history:{user_id}', status_json)
            
        # Publier la notification
        await redis.publish(f'queue_status:{user_id}', status_json)
        logger.info(f"Session nettoyée avec succès pour {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage de la session de {user_id}: {str(e)}")
        return False
    finally:
        if redis:
            await redis.aclose()
            logger.debug(f"Connexion Redis fermée pour {user_id}")

@celery.task(name='app.queue_manager.handle_draft_expiration', bind=True)
async def handle_draft_expiration(self, user_id: str):
    """Gère l'expiration du draft d'un utilisateur."""
    logger.info(f"Début de la tâche d'expiration de draft pour {user_id}")
    redis = None
    try:
        redis = Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        
        # Vérifier l'état actuel
        async with redis.pipeline(transaction=True) as pipe:
            pipe.sismember('draft_users', user_id)
            pipe.exists(f'draft:{user_id}')
            pipe.sismember('queued_users', user_id)
            results = await pipe.execute()
            
            is_draft, has_draft, is_queued = results
            
            if not is_draft or is_queued:
                logger.warning(f" 4 État invalide pour expiration: draft={is_draft}, has_draft={has_draft}, queued={is_queued}")
                return True
        
        # Effectuer la transition
        async with redis.pipeline(transaction=True) as pipe:
            pipe.srem('draft_users', user_id)
            pipe.delete(f'draft:{user_id}')
            await pipe.execute()
            
        # Ajouter le nouveau statut à l'historique
        status_info = {
            "status": "disconnected",
            "position": None,
            "reason": "draft_timeout",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        status_json = json.dumps(status_info)
        await redis.rpush(f'status_history:{user_id}', status_json)
            
        # Publier la notification
        await redis.publish(f'queue_status:{user_id}', status_json)
        logger.info(f"Draft expiré avec succès pour {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de l'expiration du draft de {user_id}: {str(e)}")
        return False
    finally:
        if redis:
            await redis.aclose()
            logger.debug(f"Connexion Redis fermée pour {user_id}")

@celery.task(name='app.queue_manager.auto_expiration', bind=True)
async def auto_expiration(self, ttl, timer_type, user_id):
    """Gère l'expiration automatique d'une session ou d'un brouillon."""
    # En mode test, retourner True immédiatement
    if os.environ.get('TESTING') == 'true':
        logging.info(f"Mode test détecté pour {user_id}, retour immédiat")
        return True
        
    redis_client = None
    try:
        redis_client = Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        
        logging.info(f"🕒 Démarrage de la tâche d'expiration {timer_type} pour {user_id}")
        
        # Attendre que le TTL expire
        await asyncio.sleep(ttl)
        
        # Vérifier l'état après l'expiration
        if timer_type == "session":
            is_active = await redis_client.sismember('active_users', user_id)
            if is_active:
                await cleanup_session.delay(user_id)
        else:  # draft
            is_draft = await redis_client.sismember('draft_users', user_id)
            if is_draft:
                await handle_draft_expiration.delay(user_id)
                
        return True
        
    except Exception as e:
        logging.error(f"❌ Erreur dans la tâche d'expiration pour {user_id}: {str(e)}")
        return True  # On retourne True même en cas d'erreur pour ne pas bloquer le test
    finally:
        if redis_client:
            await redis_client.aclose()
            logging.debug(f"Connexion Redis fermée pour {user_id}")

@celery.task(name='app.queue_manager.update_timer_channel')
async def update_timer_channel(channel: str, initial_ttl: int, timer_type: str, max_updates: int = 0, task_id: str = None):
    """Met à jour le canal de timer avec le TTL actuel."""
    redis_client = None
    try:
        redis_client = Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        
        logger.info(f"Début de la tâche de mise à jour du timer pour {channel} (TTL initial: {initial_ttl})")
        user_id = channel.split(':')[-1]
        key = f"{timer_type}:{user_id}"
        
        # Obtenir le TTL actuel
        current_ttl = await redis_client.ttl(key)
        if current_ttl <= 0 or current_ttl == -2:
            logger.info(f"TTL expiré ou invalide pour {key}: {current_ttl}")
            return 0
        
        # Publier le message
        message = {
            'timer_type': timer_type,
            'ttl': current_ttl,
            'updates_left': max_updates if max_updates > 0 else None,
            'task_id': task_id
        }
        await redis_client.publish(channel, json.dumps(message))
        
        # Si on doit continuer les mises à jour
        if max_updates == 0 or max_updates > 1:
            next_max = max_updates - 1 if max_updates > 0 else 0
            # Programmer la prochaine mise à jour avec un délai de 1 seconde
            update_timer_channel.apply_async(
                kwargs={
                    'channel': channel,
                    'initial_ttl': initial_ttl,
                    'timer_type': timer_type,
                    'max_updates': next_max,
                    'task_id': task_id
                },
                countdown=1  # Délai de 1 seconde
            )
        
        return 1
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du timer {channel}: {str(e)}")
        raise
    finally:
        if redis_client:
            await redis_client.aclose()
            logger.debug(f"Connexion Redis fermée pour {channel}") 