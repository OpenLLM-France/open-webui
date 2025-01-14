import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock fetch globalement
global.fetch = vi.fn();

// Configuration globale pour les tests
beforeAll(() => {
    // Configuration avant tous les tests
});

afterAll(() => {
    // Nettoyage après tous les tests
    vi.clearAllMocks();
});

beforeEach(() => {
    // Configuration avant chaque test
    vi.resetAllMocks();
}); 