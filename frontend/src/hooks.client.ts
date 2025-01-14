if (import.meta.env.VITE_ENABLE_CONSOLE_LOGS && typeof window !== 'undefined') {
    const methods = ['log', 'info', 'warn', 'error'] as const;
    const originalConsole = { ...console };

    for (const type of methods) {
        console[type] = (...args: unknown[]) => {
            // Appel original
            originalConsole[type](...args);

            // Envoi au serveur de développement
            try {
                const message = args
                    .map(arg => 
                        typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
                    )
                    .join(' ');

                if (import.meta.hot) {
                    import.meta.hot.send('browser-console', {
                        type,
                        message
                    });
                }
            } catch (error) {
                originalConsole.error('Error sending console log to dev server:', error);
            }
        };
    }
} 