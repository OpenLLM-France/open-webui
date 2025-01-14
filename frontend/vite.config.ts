import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		sveltekit(),
		{
			name: 'console-logger',
			configureServer(server) {
				server.ws.on('browser-console', (data, client) => {
					const { type, message } = data;
					console.log(`[Browser ${type}]`, message);
				});
			}
		}
	],
	server: {
		host: '0.0.0.0',
		port: 5173
	}
});
