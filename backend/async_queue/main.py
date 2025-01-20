from fastapi import FastAPI, HTTPException, WebSocket, Depends, WebSocketDisconnect
from queue_manager import QueueManager
from typing import Dict, Optional
import os
from redis.asyncio import Redis
from pydantic import BaseModel
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
import asyncio
from celery.result import AsyncResult

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Configuration spécifique pour le QueueManager
queue_logger = logging.getLogger('app.queue_manager')
queue_logger.setLevel(logging.DEBUG)

# Autres loggers
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class UserRequest(BaseModel):
    user_id: str

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_timer_update(self, user_id: str, timer_data: dict):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json({
                    "type": "timer",
                    **timer_data
                })
            except Exception as e:
                print(f"Erreur lors de l'envoi du message à {user_id}: {str(e)}")
                self.disconnect(user_id)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application."""
    # Initialisation
    redis = Redis(
        host=os.getenv('REDIS_HOST', 'redis'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        decode_responses=True
    )
    app.state.redis = redis
    app.state.queue_manager = QueueManager(redis)
    app.state.connection_manager = manager
    
    # Configurer le gestionnaire de connexions
    app.state.queue_manager.set_connection_manager(manager)
    
    # Démarrer le slot checker
    await app.state.queue_manager.start_slot_checker()
    
    # Configuration de Celery
    if os.environ.get('TESTING') == 'true':
        from celery import current_app as celery_app
        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
            broker_connection_retry=False,
            broker_connection_max_retries=0,
            result_backend='redis://redis:6379',
            broker_url='redis://redis:6379'
        )
        logger.info("Mode test détecté, Celery configuré en mode eager")
    
    yield
    
    # Nettoyage
    await app.state.queue_manager.stop_slot_checker()
    await redis.aclose()

app = FastAPI(lifespan=lifespan)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration Redis
async def get_redis():
    redis = Redis(
        host=os.getenv('REDIS_HOST', 'redis'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        decode_responses=True
    )
    try:
        yield redis
    finally:
        await redis.aclose()

async def get_queue_manager(redis: Redis = Depends(get_redis)) -> QueueManager:
    return QueueManager(redis)

@app.get("/health")
async def health_check():
    """Endpoint de vérification de santé."""
    return {"status": "ok"}

# Définir des modèles Pydantic pour les données
class QueueActionRequest(BaseModel):
    user_id: str

class DurationUpdate(BaseModel):
    duration: int  # en secondes

class MaxUsersUpdate(BaseModel):
    max_users: int

@app.post("/queue/join")
async def join_queue(data: QueueActionRequest, queue_manager: QueueManager = Depends(get_queue_manager)):
    """Ajoute un utilisateur à la file d'attente."""
    try:
        result = await queue_manager.add_to_queue(data.user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/queue/leave")
async def leave_queue(data: QueueActionRequest, queue_manager: QueueManager = Depends(get_queue_manager)) -> Dict:
    """Permet à un utilisateur de quitter la file d'attente ou sa session active."""
    try:
        # Vérifier l'état actuel de l'utilisateur
        current_status = await queue_manager.get_user_status(data.user_id)
        
        # Si l'utilisateur n'existe pas ou n'a jamais été dans le système
        if current_status["status"] is None:
            raise HTTPException(
                status_code=404,
                detail="Utilisateur non trouvé dans le système"
            )
        
        # Gérer selon l'état actuel
        if current_status["status"] == "waiting":
            # Retirer de la file d'attente mais garder dans accounts_queue
            success = await queue_manager.remove_from_queue(data.user_id)
            if not success:
                raise HTTPException(
                    status_code=400,
                    detail="Erreur lors de la sortie de la file d'attente"
                )
        elif current_status["status"] == "draft":
            # Retirer du draft mais garder dans accounts_queue
            async with queue_manager.redis.pipeline(transaction=True) as pipe:
                pipe.srem('draft_users', data.user_id)
                pipe.delete(f'draft:{data.user_id}')
                await pipe.execute()
        elif current_status["status"] == "connected":
            # Retirer de la session active mais garder dans accounts_queue
            async with queue_manager.redis.pipeline(transaction=True) as pipe:
                pipe.srem('active_users', data.user_id)
                pipe.delete(f'session:{data.user_id}')
                await pipe.execute()
        elif current_status["status"] == "disconnected":
            # Déjà déconnecté, rien à faire
            return {
                "previous_status": "disconnected",
                "new_status": "disconnected",
                "user_id": data.user_id,
                "in_accounts_queue": True
            }
        
        # Récupérer le nouveau statut (devrait être "disconnected" car dans accounts_queue)
        new_status = await queue_manager.get_user_status(data.user_id)
        
        return {
            "previous_status": current_status["status"],
            "new_status": new_status["status"],
            "user_id": data.user_id,
            "in_accounts_queue": await queue_manager.redis.sismember('accounts_queue', data.user_id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/queue/confirm")
async def confirm_queue_connection(data: QueueActionRequest, queue_manager: QueueManager = Depends(get_queue_manager)) -> Dict:
    """Confirme la connexion d'un utilisateur."""
    try:
        result = await queue_manager.confirm_connection(data.user_id)
        if result:
            logger.info(f"✅ Confirmation réussie pour {data.user_id}, résultat: {result}")
            return {"status": "success", "message": "Connexion confirmée", "result": result, "session_duration": result["session_duration"]}
        else:
            logger.info(f"ℹ️ Confirmation impossible pour {data.user_id} - Pas de slot draft disponible, résultat: {result}")
            raise HTTPException(
                status_code=400,
                detail=f"No draft slot available, result: {result}"
            )
    except HTTPException as he:
        logger.error(f"❌ Erreur HTTP lors de la confirmation pour {data.user_id}: {str(he)}")
        raise he
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors de la confirmation pour {data.user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/queue/status/{user_id}")
async def get_status(data: QueueActionRequest, queue_manager: QueueManager = Depends(get_queue_manager)):
    """Récupère le statut d'un utilisateur."""
    user_id = data.user_id
    try:
        status = await queue_manager.get_user_status(user_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/queue/heartbeat/{user_id}")
async def heartbeat_path(
    user_id: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
) -> Dict:
    """Endpoint pour maintenir la session active (via paramètre URL)."""
    success = await queue_manager.extend_session(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="No active session found")
    
    # Vérifier que l'utilisateur est toujours dans active_users
    is_active = await queue_manager.redis.sismember("active_users", user_id)
    if not is_active:
        raise HTTPException(status_code=404, detail="User not in active users")
    
    # Récupérer le TTL actuel
    ttl = await queue_manager.redis.ttl(f"session:{user_id}")
    
    return {
        "status": "extended",
        "user_id": user_id,
        "ttl": ttl
    }

@app.post("/queue/heartbeat")
async def heartbeat_body(
    data: QueueActionRequest,
    queue_manager: QueueManager = Depends(get_queue_manager)
) -> Dict:
    """Endpoint pour maintenir la session active (via corps JSON)."""
    return await heartbeat_path(data.user_id, queue_manager)

@app.get("/queue/metrics")
async def get_metrics(queue_manager: QueueManager = Depends(get_queue_manager)) -> Dict:
    """Endpoint pour obtenir les métriques de la file d'attente."""
    metrics = await queue_manager.get_metrics()
    return metrics

@app.get("/queue/get_users")
async def get_users(queue_manager: QueueManager = Depends(get_queue_manager)) -> Dict:
    """Récupère les listes d'utilisateurs en attente, en draft et actifs."""
    try:
        # Récupérer les utilisateurs en attente
        waiting_users = await queue_manager.redis.lrange('waiting_queue', 0, -1)
        waiting_users = [user.decode('utf-8') if isinstance(user, bytes) else user for user in waiting_users]
        
        # Récupérer les utilisateurs en draft
        draft_users = await queue_manager.redis.smembers('draft_users')
        draft_users = [user.decode('utf-8') if isinstance(user, bytes) else user for user in draft_users]
        
        # Récupérer les utilisateurs actifs
        active_users = await queue_manager.redis.smembers('active_users')
        active_users = [user.decode('utf-8') if isinstance(user, bytes) else user for user in active_users]
        
        return {
            "waiting_users": waiting_users,
            "draft_users": draft_users,
            "active_users": active_users
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queue/timers")
async def get_timers(data: QueueActionRequest, queue_manager: QueueManager = Depends(get_queue_manager)) -> Dict:
    """Endpoint pour obtenir les timers actifs d'un utilisateur."""
    timers = await queue_manager.get_timers(data.user_id)
    # Nettoyer la réponse pour la rendre sérialisable
    if "task" in timers:
        if asyncio.iscoroutine(timers["task"]):
            # Si c'est une coroutine, on l'attend
            timers["task"] = await timers["task"]
        elif isinstance(timers["task"], AsyncResult):
            # Si c'est un AsyncResult de Celery, on récupère le résultat
            try:
                timers["task"] = await asyncio.wait_for(
                    asyncio.to_thread(timers["task"].get),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                timers["status"] = "error"
                timers["error"] = "The operation timed out."
            except Exception as e:
                timers["status"] = "error"
                timers["error"] = str(e)
        else:
            # Si c'est une autre valeur, on la garde telle quelle
            pass

    return timers

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            # Attendre les messages du client
            data = await websocket.receive_text()
            # Pour l'instant, nous ne faisons rien avec les messages reçus
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f"Erreur WebSocket pour {user_id}: {str(e)}")
        manager.disconnect(user_id) 

@app.post("/queue/cleanup_all")
async def cleanup_all(queue_manager: QueueManager = Depends(get_queue_manager)):
    """Nettoie toutes les files d'attente."""
    try:
        result = await queue_manager.cleanup_all()
        if result:
            return {"status": "success", "message": "Files d'attente nettoyées"}
        return {"status": "error", "message": "Erreur lors du nettoyage"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

@app.post("/queue/update_draft_duration")
async def update_draft_duration(
    data: DurationUpdate,
    queue_manager: QueueManager = Depends(get_queue_manager)
) -> Dict:
    """Met à jour la durée du draft."""
    try:
        success = await queue_manager.update_draft_duration(data.duration)
        if success:
            return {
                "status": "success",
                "message": f"Durée du draft mise à jour: {data.duration} secondes",
                "response": json.dumps(success)
            }
        raise HTTPException(
            status_code=400,
            detail="Erreur lors de la mise à jour de la durée du draft"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/queue/update_session_duration")
async def update_session_duration(
    data: DurationUpdate,
    queue_manager: QueueManager = Depends(get_queue_manager)
) -> Dict:
    """Met à jour la durée de la session."""
    try:
        success = await queue_manager.update_session_duration(data.duration)
        if success:
            return {
                "status": "success",
                "message": f"Durée de session mise à jour: {data.duration} secondes",
                "response": json.dumps(success)
            }
        raise HTTPException(
            status_code=400,
            detail="Erreur lors de la mise à jour de la durée de session"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/queue/update_max_users")
async def update_max_users(
    data: MaxUsersUpdate,
    queue_manager: QueueManager = Depends(get_queue_manager)
) -> Dict:
    """Met à jour le nombre maximum d'utilisateurs actifs."""
    try:
        if data.max_users < 1:
            raise HTTPException(
                status_code=400,
                detail="Le nombre maximum d'utilisateurs doit être supérieur à 0"
            )
            
        success = await queue_manager.update_max_users(data.max_users)
        if success:
            return {
                "status": "success",
                "message": f"Nombre maximum d'utilisateurs mis à jour: {data.max_users}",
                "response": json.dumps(success)
            }
        raise HTTPException(
            status_code=400,
            detail="Erreur lors de la mise à jour du nombre maximum d'utilisateurs"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 