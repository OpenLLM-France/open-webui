export interface UserRequest {
    user_id: string;
}

// Types pour les réponses de l'API
export interface QueueStatus {
    user_id: string;
    status: 'waiting' | 'draft' | 'connected' | 'disconnected';
    position: number;
    remaining_time: number;
    estimated_wait_time: number;
    timestamp: string;
}

export interface QueueJoinResponse {
    last_status: string | null;
    last_position: number | null;
    commit_status: 'waiting' | 'draft' | 'connected' | 'disconnected';
    commit_position: number;
}

export interface QueueMetrics {
    active_users: number;
    waiting_users: number;
    total_slots: number;
    average_wait_time: number;
    average_session_time: number;
}

export interface TimerInfo {
    timer_type: 'draft' | 'session';
    ttl: number;
    total_duration: number;
    channel: string;
}

export interface ConnectionResponse {
    session_duration: number;
    total_duration: number;
}

export interface ApiResponse {
    success: boolean;
    position?: number;
    detail?: string;
}

// Type pour le mock de fetch
export interface MockFetch {
    ok: boolean;
    json: () => Promise<QueueStatus | QueueMetrics | TimerInfo | ApiResponse | QueueJoinResponse | ConnectionResponse>;
    status?: number;
    statusText?: string;
}

export interface GetUsersResponse {
    waiting_users: string[];
    draft_users: string[];
    active_users: string[];
}
