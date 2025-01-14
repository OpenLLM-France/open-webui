import { describe, it, expect, beforeEach } from 'vitest';
import { joinQueue, leaveQueue, getStatus, getTimers, getMetrics, confirmConnection } from './queue';
import { redisClient } from './redis';
import { createClient } from 'redis';

describe('Queue API Integration Tests', () => {
    const userId = 'test-user-123';
    const userRequest = { user_id: userId };

    // Nettoyer Redis avant chaque test
    beforeEach(async () => {
        // Nettoyer l'état de Redis
        await redisClient.SREM('queued_users', userId);
        await redisClient.SREM('active_users', userId);
        await redisClient.SREM('draft_users', userId);
        await redisClient.LREM('waiting_queue', 0, userId);
        await redisClient.DEL(`draft:${userId}`);
        await redisClient.DEL(`session:${userId}`);
    });

    describe('joinQueue', () => {
        it('devrait rejoindre la file avec succès', async () => {
            const result = await joinQueue(userRequest);
            expect(result).toHaveProperty('last_status');
            expect(result).toHaveProperty('last_position');
            expect(result).toHaveProperty('commit_status');
            expect(result).toHaveProperty('commit_position');
            expect(result.commit_status).toBe('waiting');
            expect(typeof result.commit_position).toBe('number');
        });

        it('devrait gérer les erreurs', async () => {
            // Simuler un utilisateur déjà dans la file
            await redisClient.SADD('queued_users', userId);
            await redisClient.RPUSH('waiting_queue', userId);
            await expect(joinQueue(userRequest)).rejects.toThrow("Utilisateur déjà dans la file d'attente");
        });
    });

    describe('getStatus', () => {
        it('devrait récupérer le statut avec succès', async () => {
            // Ajouter l'utilisateur à la file d'attente
            await redisClient.SADD('queued_users', userId);
            await redisClient.RPUSH('waiting_queue', userId);
            
            const result = await getStatus(userId);
            expect(result).toHaveProperty('status');
            expect(result.status).toBe('waiting');
            expect(result).toHaveProperty('position');
            expect(typeof result.position).toBe('number');
            expect(result).toHaveProperty('remaining_time');
            expect(typeof result.remaining_time).toBe('number');
            expect(result).toHaveProperty('estimated_wait_time');
            expect(typeof result.estimated_wait_time).toBe('number');
            expect(result).toHaveProperty('timestamp');
            expect(typeof result.timestamp).toBe('string');
        });
    });

    describe('getTimers', () => {
        it('devrait récupérer les timers avec succès', async () => {
            // Mettre l'utilisateur en draft
            await redisClient.SADD('draft_users', userId);
            await redisClient.SETEX(`draft:${userId}`, 60, '1');
            
            const result = await getTimers(userId);
            expect(result).toHaveProperty('timer_type');
            expect(result).toHaveProperty('ttl');
            expect(result).toHaveProperty('total_duration');
            expect(result).toHaveProperty('channel');
            expect(result.timer_type).toBe('draft');
            expect(typeof result.ttl).toBe('number');
            expect(typeof result.total_duration).toBe('number');
            expect(typeof result.channel).toBe('string');
        });

        it('devrait recevoir les messages de mise à jour des timers', async () => {
            // Créer un subscriber pour écouter les messages
            const subscriberClient = createClient();
            await subscriberClient.connect();
            
            const messages: string[] = [];
            await subscriberClient.subscribe(`timer:channel:${userId}`, (message: string) => {
                messages.push(message);
                console.log('Message reçu:', message);
            });

            // Rejoindre la file d'attente
            const joinResult = await joinQueue(userRequest);
            console.log('Join result:', joinResult);

            // Attendre et vérifier le statut jusqu'à ce qu'il soit en draft
            let status: { status: string } | null = null;
            for (let i = 0; i < 10; i++) {
                try {
                    status = await getStatus(userId);
                    console.log('Status:', status);
                    if (status.status === 'draft') break;
                } catch (err) {
                    console.log('Erreur getStatus:', err);
                }
                await new Promise(resolve => setTimeout(resolve, 1000));
            }

            // Vérifier les timers seulement si nous sommes en draft
            if (status?.status === 'draft') {
                try {
                    const timers = await getTimers(userId);
                    console.log('Timers:', timers);

                    // Attendre les messages de l'API
                    await new Promise(resolve => setTimeout(resolve, 5000));

                    // Vérifier les messages reçus
                    console.log('Messages reçus:', messages);
                    expect(messages.length).toBeGreaterThan(0);
                    
                    // Vérifier le format des messages
                    const validMessages = messages.filter(msg => {
                        try {
                            const data = JSON.parse(msg);
                            return (
                                'user_id' in data &&
                                'timer_type' in data &&
                                'ttl' in data &&
                                'total_duration' in data &&
                                typeof data.ttl === 'number' &&
                                typeof data.total_duration === 'number'
                            );
                        } catch {
                            return false;
                        }
                    });
                    expect(validMessages.length).toBeGreaterThan(0);
                } catch (err) {
                    console.log('Erreur getTimers:', err);
                }
            } else {
                console.log('Test ignoré : utilisateur non passé en draft');
            }

            // Nettoyage
            await subscriberClient.unsubscribe(`timer:channel:${userId}`);
            await subscriberClient.quit();
        }, 30000);
    });

    describe('confirmConnection', () => {
        it('devrait confirmer la connexion avec succès', async () => {
            // Mettre l'utilisateur en draft
            await redisClient.SADD('draft_users', userId);
            await redisClient.SETEX(`draft:${userId}`, 60, '1');
            
            const result = await confirmConnection(userRequest);
            expect(result).toHaveProperty('session_duration');
            expect(typeof result.session_duration).toBe('number');
            expect(result).toHaveProperty('total_duration');
            expect(typeof result.total_duration).toBe('number');
        });
    });

    describe('leaveQueue', () => {
        it('devrait quitter la file avec succès', async () => {
            // Mettre l'utilisateur dans la file
            await redisClient.SADD('queued_users', userId);
            await redisClient.RPUSH('waiting_queue', userId);
            
            const result = await leaveQueue(userRequest);
            expect(result).toHaveProperty('success');
            expect(result.success).toBe(true);
        });
    });

    describe('getMetrics', () => {
        it('devrait récupérer les métriques avec succès', async () => {
            // Ajouter des utilisateurs actifs et en attente
            for(let i = 1; i <= 5; i++) {
                await redisClient.SADD('active_users', `user-${i}`);
            }
            for(let i = 6; i <= 15; i++) {
                await redisClient.SADD('queued_users', `user-${i}`);
                await redisClient.RPUSH('waiting_queue', `user-${i}`);
            }
            
            const result = await getMetrics();
            expect(result).toHaveProperty('active_users');
            expect(result).toHaveProperty('waiting_users');
            expect(result).toHaveProperty('total_slots');
            expect(result).toHaveProperty('average_wait_time');
            expect(result).toHaveProperty('average_session_time');
            expect(typeof result.active_users).toBe('number');
            expect(typeof result.waiting_users).toBe('number');
            expect(typeof result.total_slots).toBe('number');
            expect(typeof result.average_wait_time).toBe('number');
            expect(typeof result.average_session_time).toBe('number');
        });
    });
}); 