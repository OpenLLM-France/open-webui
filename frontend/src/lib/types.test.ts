import { describe, it, expect } from 'vitest';
import type { UserRequest, QueueStatus, QueueMetrics, TimerInfo } from './types';

describe('Types', () => {
    it('devrait créer une requête utilisateur valide', () => {
        const userRequest: UserRequest = {
            user_id: 'test-123'
        };
        expect(userRequest.user_id).toBe('test-123');
    });

    it('devrait créer un statut de file valide', () => {
        const status: QueueStatus = {
            status: 'waiting',
            position: 1
        };
        expect(status.status).toBe('waiting');
        expect(status.position).toBe(1);
    });

    it('devrait créer des métriques de file valides', () => {
        const metrics: QueueMetrics = {
            active_users: 5,
            waiting_users: 10,
            total_slots: 50
        };
        expect(metrics.active_users).toBe(5);
        expect(metrics.waiting_users).toBe(10);
        expect(metrics.total_slots).toBe(50);
    });

    it('devrait créer des informations de timer valides', () => {
        const timer: TimerInfo = {
            timer_type: 'draft',
            ttl: 60
        };
        expect(timer.timer_type).toBe('draft');
        expect(timer.ttl).toBe(60);
    });
}); 