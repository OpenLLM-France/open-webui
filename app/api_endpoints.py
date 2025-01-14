from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Optional
import asyncio
from .queue_manager import QueueManager
from redis.asyncio import Redis
import os
import logging

logger = logging.getLogger('test_logger')

router = APIRouter()

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

async def confirm_connection(user_id: str, queue_manager: QueueManager):
    """Confirme la connexion d'un utilisateur."""
    try:
        result = await queue_manager.confirm_connection(user_id)
        if result:
            logger.info(f"✅ Confirmation réussie pour {user_id}")
            return True
        else:
            logger.info(f"ℹ️ Confirmation impossible pour {user_id}")
            return False
    except Exception as e:
        logger.error(f"❌ Erreur lors de la confirmation pour {user_id}: {str(e)}")
        return False

@router.get("/queue/timers/{user_id}")
async def get_timers(
    user_id: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
) -> Dict:
    """Récupère les timers actifs pour un utilisateur."""
    try:
        # Vérifier l'état actuel de l'utilisateur
        current_status = await queue_manager.get_user_status(user_id)
        
        # Si l'utilisateur n'est pas dans un état avec timer, retourner un objet vide
        if current_status["status"] not in ["draft", "connected"]:
            return {}
            
        # Récupérer le TTL selon l'état
        key = f'draft:{user_id}' if current_status["status"] == "draft" else f'session:{user_id}'
        ttl = await queue_manager.redis.ttl(key)
        
        # Si pas de timer actif, retourner un objet vide
        if ttl < 0:
            return {}
            
        # Si nous avons un TTL valide, retourner les informations du timer
        return {
            "ttl": ttl
        }
        
    except Exception as e:
        # En cas d'erreur, retourner un objet vide
        return {}

@router.post("/test/accounts_queue/add/{user_id}")
async def test_add_to_accounts(
    user_id: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
) -> Dict:
    """Endpoint de test pour ajouter un utilisateur à la file d'attente et vérifier son ajout à accounts_queue."""
    try:
        # Ajouter l'utilisateur à la file d'attente
        add_result = await queue_manager.add_to_queue(user_id)
        
        # Vérifier si l'utilisateur est dans accounts_queue
        is_in_accounts = await queue_manager.redis.sismember('accounts_queue', user_id)
        
        return {
            "add_result": add_result,
            "in_accounts_queue": is_in_accounts,
            "user_id": user_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/session/expire/{user_id}")
async def test_session_expiration(
    user_id: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
) -> Dict:
    """Endpoint de test pour simuler l'expiration d'une session active."""
    try:
        # Vérifier si l'utilisateur est actif
        is_active = await queue_manager.redis.sismember('active_users', user_id)
        if not is_active:
            raise HTTPException(status_code=400, detail="L'utilisateur n'est pas actif")
            
        # Forcer l'expiration de la session en supprimant la clé
        await queue_manager.redis.delete(f'session:{user_id}')
        
        # Attendre un peu pour laisser le temps au timer de détecter l'expiration
        await asyncio.sleep(2)
        
        # Vérifier le nouvel état
        new_status = await queue_manager.get_user_status(user_id)
        
        return {
            "user_id": user_id,
            "initial_state": "active",
            "final_state": new_status,
            "session_key_exists": await queue_manager.redis.exists(f'session:{user_id}'),
            "still_active": await queue_manager.redis.sismember('active_users', user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/draft/expire/{user_id}")
async def test_draft_expiration(
    user_id: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
) -> Dict:
    """Endpoint de test pour simuler l'expiration d'un draft."""
    try:
        # Vérifier si l'utilisateur est en draft
        is_draft = await queue_manager.redis.sismember('draft_users', user_id)
        if not is_draft:
            raise HTTPException(status_code=400, detail="L'utilisateur n'est pas en draft")
            
        # Forcer l'expiration du draft en supprimant la clé
        await queue_manager.redis.delete(f'draft:{user_id}')
        
        # Attendre un peu pour laisser le temps au timer de détecter l'expiration
        await asyncio.sleep(2)
        
        # Vérifier le nouvel état
        new_status = await queue_manager.get_user_status(user_id)
        
        return {
            "user_id": user_id,
            "initial_state": "draft",
            "final_state": new_status,
            "draft_key_exists": await queue_manager.redis.exists(f'draft:{user_id}'),
            "still_in_draft": await queue_manager.redis.sismember('draft_users', user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test/accounts_queue/status/{user_id}")
async def test_get_account_status(
    user_id: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
) -> Dict:
    """Endpoint de test pour vérifier le statut d'un utilisateur dans accounts_queue."""
    try:
        # Vérifier tous les états possibles
        is_in_accounts = await queue_manager.redis.sismember('accounts_queue', user_id)
        current_status = await queue_manager.get_user_status(user_id)
        
        # Vérifier les autres états pour plus de détails
        async with queue_manager.redis.pipeline(transaction=True) as pipe:
            pipe.sismember('active_users', user_id)
            pipe.sismember('draft_users', user_id)
            pipe.lpos('waiting_queue', user_id)
            pipe.sismember('queued_users', user_id)
            is_active, is_draft, waiting_pos, is_queued = await pipe.execute()
        
        return {
            "user_id": user_id,
            "in_accounts_queue": is_in_accounts,
            "current_status": current_status,
            "detailed_state": {
                "is_active": is_active,
                "is_draft": is_draft,
                "waiting_position": waiting_pos,
                "is_queued": is_queued
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

@router.post("/queue/leave/{user_id}")
async def leave_queue(
    user_id: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
) -> Dict:
    """Permet à un utilisateur de quitter la file d'attente ou sa session active."""
    try:
        # Vérifier l'état actuel de l'utilisateur
        current_status = await queue_manager.get_user_status(user_id)
        
        # Si l'utilisateur n'est pas dans le système, retourner une erreur
        if current_status["status"] is None:
            raise HTTPException(
                status_code=404,
                detail="Utilisateur non trouvé dans le système"
            )
        
        # Retirer l'utilisateur selon son état
        if current_status["status"] == "waiting":
            success = await queue_manager.remove_from_queue(user_id)
            if not success:
                raise HTTPException(
                    status_code=400,
                    detail="Erreur lors de la sortie de la file d'attente"
                )
        elif current_status["status"] == "draft":
            async with queue_manager.redis.pipeline(transaction=True) as pipe:
                pipe.srem('draft_users', user_id)
                pipe.delete(f'draft:{user_id}')
                pipe.srem('accounts_queue', user_id)
                await pipe.execute()
        elif current_status["status"] == "connected":
            async with queue_manager.redis.pipeline(transaction=True) as pipe:
                pipe.srem('active_users', user_id)
                pipe.delete(f'session:{user_id}')
                pipe.srem('accounts_queue', user_id)
                await pipe.execute()
        
        # Récupérer le nouveau statut
        new_status = await queue_manager.get_user_status(user_id)
        
        return {
            "previous_status": current_status["status"],
            "new_status": new_status["status"],
            "user_id": user_id
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/queue/join/{user_id}")
async def join_queue(
    user_id: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
) -> Dict:
    """Permet à un utilisateur de rejoindre la file d'attente."""
    try:
        # Vérifier l'état actuel de l'utilisateur
        current_status = await queue_manager.get_user_status(user_id)
        last_position = None if current_status["status"] is None else current_status.get("position")
        
        # Si l'utilisateur est déjà dans un état actif, retourner une erreur
        if current_status["status"] in ["waiting", "draft", "connected"]:
            raise HTTPException(
                status_code=400,
                detail="Utilisateur déjà dans la file d'attente"
            )
        
        # Ajouter l'utilisateur à la file
        result = await queue_manager.add_to_queue(user_id)
        
        # Récupérer le nouveau statut
        new_status = await queue_manager.get_user_status(user_id)
        new_position = new_status.get("position", None)
        
        return {
            "last_status": current_status["status"],
            "last_position": last_position,
            "commit_status": new_status["status"],
            "commit_position": new_position
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        if "déjà dans la file d'attente" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/queue/heartbeat/{user_id}")
async def heartbeat(
    user_id: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
) -> Dict:
    """Prolonge la session d'un utilisateur actif."""
    try:
        # Vérifier si l'utilisateur est actif
        is_active = await queue_manager.redis.sismember('active_users', user_id)
        if not is_active:
            raise HTTPException(
                status_code=404,
                detail="Utilisateur non trouvé ou non actif"
            )
        
        # Prolonger la session
        success = await queue_manager.extend_session(user_id)
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Erreur lors de la prolongation de la session"
            )
        
        # Récupérer le TTL actuel
        ttl = await queue_manager.redis.ttl(f'session:{user_id}')
        
        return {
            "status": "extended",
            "user_id": user_id,
            "ttl": ttl
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 