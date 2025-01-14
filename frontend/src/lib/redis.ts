import { createClient } from 'redis';
import type { RedisClientType } from 'redis';

// Créer un client Redis avec les paramètres de connexion
const client = createClient({
    url: process.env.REDIS_URL || 'redis://localhost:6379',
    socket: {
        reconnectStrategy: retries => Math.min(retries * 50, 1000)
    }
});

// Connexion à Redis
client.connect().catch((error: Error) => console.error('Redis Connection Error:', error));

// Gérer les erreurs de connexion
client.on('error', (error: Error) => console.error('Redis Client Error:', error));

// Wrapper pour les méthodes Redis
const wrappedClient = {
    async SREM(key: string, member: string): Promise<number> {
        return client.SREM(key, member);
    },

    async SADD(key: string, member: string): Promise<number> {
        return client.SADD(key, member);
    },

    async LREM(key: string, count: number, element: string): Promise<number> {
        return client.LREM(key, count, element);
    },

    async RPUSH(key: string, element: string): Promise<number> {
        return client.RPUSH(key, element);
    },

    async LPOS(key: string, element: string): Promise<number | null> {
        return client.LPOS(key, element);
    },

    async EXISTS(key: string): Promise<number> {
        return client.EXISTS(key);
    },

    async SETEX(key: string, seconds: number, value: string): Promise<string | null> {
        return client.SETEX(key, seconds, value);
    },

    async DEL(key: string): Promise<number> {
        return client.DEL(key);
    }
};

export { wrappedClient as redisClient }; 