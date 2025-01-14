import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { cleanup } from '@testing-library/svelte';

// Nettoyage automatique après chaque test
afterEach(() => {
  cleanup();
});

// Configuration de l'environnement de test
vi.mock('$app/environment', () => ({
  browser: true,
  dev: true,
  building: false,
}));

// Mock des variables d'environnement
vi.mock('$env/dynamic/public', () => ({
  env: {
    PUBLIC_API_URL: 'http://localhost:8000'
  }
}));

// Mock de Tailwind CSS
vi.mock('tailwindcss', () => ({
  default: () => ({
    config: {
      content: [],
      theme: {
        extend: {},
      },
      plugins: [],
    },
  }),
}));

// Configuration globale de l'environnement de test
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
}); 