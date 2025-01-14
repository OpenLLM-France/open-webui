#!/usr/bin/env python3
"""
Script de test de charge pour le système de file d'attente.

Ce module permet de simuler :
- Des utilisateurs individuels
- Des groupes d'utilisateurs simultanés
- Des scénarios de montée en charge
- Des comportements utilisateurs variés
"""

import asyncio
import aiohttp
import redis.asyncio as redis
import json
import click
import random
from datetime import datetime
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueueClient:
    """Client simulé pour le système de file d'attente."""
    
    def __init__(self, user_id: str, base_url: str = "http://localhost:8000"):
        self.user_id = user_id
        self.base_url = base_url
        self.session = None
        self.redis = None
        self.connected = False

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        self.redis = await redis.Redis(decode_responses=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
        await self.redis.close()

    async def join_queue(self) -> Dict:
        """Rejoint la file d'attente."""
        async with self.session.post(f"{self.base_url}/queue/join/{self.user_id}") as response:
            return await response.json()

    async def monitor_status(self):
        """Surveille le statut dans la file d'attente."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f'queue_status:{self.user_id}')
        
        try:
            while not self.connected:
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    data = json.loads(message['data'])
                    if data.get('status') == 'slot_available':
                        # Simule un délai de réaction utilisateur
                        await asyncio.sleep(random.uniform(0.5, 2))
                        await self.confirm_connection()
                    elif data.get('status') == 'connected':
                        self.connected = True
                        logger.info(f"User {self.user_id} connected!")
                        break
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe()

    async def confirm_connection(self):
        """Confirme la connexion quand un slot est disponible."""
        async with self.session.post(f"{self.base_url}/queue/confirm/{self.user_id}") as response:
            return await response.json()

class LoadTest:
    """Gestionnaire de tests de charge."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    async def run_single_user(self, user_id: str):
        """Simule le comportement d'un seul utilisateur."""
        async with QueueClient(user_id, self.base_url) as client:
            await client.join_queue()
            await client.monitor_status()

    async def run_user_group(self, size: int, group_id: str):
        """Simule un groupe d'utilisateurs se connectant simultanément."""
        users = [self.run_single_user(f"user_{group_id}_{i}") for i in range(size)]
        await asyncio.gather(*users)

    async def run_load_test(self, total_users: int, batch_size: int, delay: float):
        """
        Simule une montée en charge progressive.
        
        Args:
            total_users: Nombre total d'utilisateurs à simuler
            batch_size: Nombre d'utilisateurs par groupe
            delay: Délai entre chaque groupe (en secondes)
        """
        start_time = datetime.now()
        logger.info(f"Starting load test with {total_users} users")

        for i in range(0, total_users, batch_size):
            group_size = min(batch_size, total_users - i)
            logger.info(f"Launching group {i//batch_size + 1} with {group_size} users")
            await self.run_user_group(group_size, f"group_{i//batch_size}")
            await asyncio.sleep(delay)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Load test completed in {duration:.2f} seconds")

@click.group()
def cli():
    """Commandes de test de charge pour le système de file d'attente."""
    pass

@cli.command()
@click.option('--users', default=100, help='Nombre total d\'utilisateurs')
@click.option('--batch-size', default=10, help='Taille des groupes d\'utilisateurs')
@click.option('--delay', default=5.0, help='Délai entre les groupes (secondes)')
def load(users: int, batch_size: int, delay: float):
    """Lance un test de charge progressif."""
    load_test = LoadTest()
    asyncio.run(load_test.run_load_test(users, batch_size, delay))

@cli.command()
@click.option('--size', default=50, help='Nombre d\'utilisateurs dans le groupe')
def group(size: int):
    """Simule un groupe d'utilisateurs se connectant simultanément."""
    load_test = LoadTest()
    asyncio.run(load_test.run_user_group(size, "test_group"))

@cli.command()
@click.argument('user_id')
def single(user_id: str):
    """Simule un utilisateur unique."""
    load_test = LoadTest()
    asyncio.run(load_test.run_single_user(user_id))

if __name__ == '__main__':
    cli() 