#!/usr/bin/env python3

import sys
import time
import logging
from typing import Optional, Any
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.queue import queue, QueueStatus, QueueMetrics, JoinRequest, ConfirmRequest, ConfirmResponse, DeleteRequest, MetricsRequest
from fastapi import APIRouter, HTTPException, status
from async_queue.main import QueueManager
from fastapi import FastAPI, HTTPException, WebSocket, Depends, WebSocketDisconnect
from contextlib import asynccontextmanager
import os
from redis.asyncio import Redis
from typing import Dict
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])


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
        host=os.getenv('REDIS_HOST', 'localhost'),
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
            result_backend='redis://localhost:6379',
            broker_url='redis://localhost:6379'
        )
        logger.info("Mode test détecté, Celery configuré en mode eager")
    
    yield
    
    # Nettoyage
    await app.state.queue_manager.stop_slot_checker()
    await redis.aclose()
router = APIRouter(lifespan=lifespan)



router.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration Redis
async def get_redis():
    redis = Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
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

@router.get("/health")
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
############################
# Join Queue
############################

@router.post("/join", response_model=dict[str, int])
async def join(request: JoinRequest, queue_manager: QueueManager = Depends(get_queue_manager)):

    """Ajoute un utilisateur à la file d'attente."""
    try:
        result = await queue_manager.add_to_queue(request.user_id)

        logging.info(f"join {request.user_id} result: {result}")
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Unknown user {request.user_id}'
            )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

############################
# Get Queue Status
############################

@router.get("/status/{user_id}", response_model=dict[str, Any])
async def get_status(user_id: str):
    log.debug(f'-> status({user_id})')
    out = queue.status(user_id)
    
    if out is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Unknown user {user_id}'
        )
    
    return out

###########################Leave
# Confirm Queue Position
############################

@router.post("/confirm", response_model=ConfirmResponse)
async def confirm(request: ConfirmRequest):
    user_id = request.user_id
    log.debug(f'-> confirm({user_id})')
    
    now = int(time.time())
    session_duration = queue.confirm(user_id, now)
    
    if session_duration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Unknown user {user_id}'
        )
    
    return ConfirmResponse(
        status=QueueStatus.CONNECTED,
        session_duration=session_duration,
        token=' '.join([str(now), user_id]),
        signature=None  # TODO
    )

############################
# Queue Maintenance
############################

@router.post("/idle", response_model=dict)
async def idle():
    queue.idle()
    return {}


############################
# Queue Metrics
############################

@router.post("/metrics", response_model=QueueMetrics)
async def get_metrics(request: MetricsRequest):
    return queue.metrics(user_id=request.user_id)

############################
# Queue Leave
############################

@router.post("/leave", response_model=dict)
async def delete(data: QueueActionRequest, queue_manager: QueueManager = Depends(get_queue_manager)):
    """Permet à un utilisateur de quitter la file d'attente ou sa session active."""
    try:
        # Vérifier l'état actuel de l'utilisateur
        user_id = data.user_id
        queue.delete(user_id)
        current_status = await queue_manager.get_user_status(user_id)
        
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
