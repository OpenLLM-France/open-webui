// Fonction pour détecter l'environnement d'exécution
const isBrowser = typeof window !== 'undefined' && typeof window.fetch === 'function';

// Type pour les options de fetch qui fonctionne dans les deux environnements
type UniversalRequestInit = Omit<RequestInit, 'body'> & {
    body?: string | URLSearchParams | Blob | ArrayBuffer | FormData | null;
};

// Fonction fetch personnalisée qui s'adapte à l'environnement
const customFetch = async (url: string, options?: UniversalRequestInit): Promise<Response> => {
    try {
        if (isBrowser) {
            return await window.fetch(url, options as RequestInit);
        }
        
        const nodeFetch = (await import('node-fetch')).default;
        return await nodeFetch(url, options as any) as unknown as Response;
    } catch (error) {
        if (error instanceof TypeError && error.message === 'Failed to fetch') {
            throw new Error('Le serveur n\'est pas disponible');
        }
        throw error;
    }
};

export default customFetch; 