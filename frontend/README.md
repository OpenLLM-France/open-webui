# Frontend Queue System

Ce dossier contient l'application frontend du système de file d'attente, développée avec SvelteKit et TypeScript.

## Structure du Projet

```
frontend/
├── src/                    # Code source
│   ├── lib/               # Composants et utilitaires réutilisables
│   │   ├── queue.ts      # Client API pour la file d'attente
│   │   ├── types.ts      # Types TypeScript partagés
│   │   └── *.test.ts     # Tests unitaires et d'intégration
│   ├── routes/           # Pages et composants de routage SvelteKit
│   └── app.html          # Template HTML principal
├── static/               # Fichiers statiques
├── tests/               # Configuration des tests
└── vite.config.ts       # Configuration de Vite et Vitest
```

## Tests

Le projet utilise Vitest comme framework de test avec plusieurs types de tests :

### Tests Unitaires
Les tests unitaires utilisent des mocks pour simuler les appels API et peuvent être exécutés sans dépendances externes.

```bash
# Lancer les tests unitaires en mode watch
npm test

# Lancer les tests unitaires une seule fois
npm run test:run
```

### Tests d'Intégration
Les tests d'intégration nécessitent que le serveur backend soit en marche sur `http://localhost:8000`.

```bash
# Lancer les tests d'intégration
npm run test:integration

# Lancer tous les tests (unitaires + intégration)
npm run test:all
```

### Autres Commandes de Test

```bash
# Interface utilisateur des tests
npm run test:ui

# Rapport de couverture de code
npm run test:coverage

# Mode watch pour tous les tests
npm run test:all

# Exécution unique de tous les tests
npm run test:run:all
```

## Développement

```bash
# Installation des dépendances
npm install

# Démarrer le serveur de développement
npm run dev

# Construire pour la production
npm run build

# Prévisualiser la version de production
npm run preview
```

## Vérification des Types

```bash
# Vérification unique
npm run check

# Vérification continue
npm run check:watch
```

## Notes sur les Tests

- Les tests unitaires (`*.test.ts`) utilisent des mocks pour simuler les appels API
- Les tests d'intégration (`*.integration.test.ts`) nécessitent un serveur backend fonctionnel
- La couverture de code peut être visualisée après avoir exécuté `npm run test:coverage`
- L'interface utilisateur des tests (`npm run test:ui`) offre une visualisation interactive des tests

## Configuration

- `vite.config.ts` : Configuration de Vite et des tests
- `vitest.setup.ts` : Configuration globale des tests
- `tsconfig.json` : Configuration TypeScript
- `svelte.config.js` : Configuration Svelte
