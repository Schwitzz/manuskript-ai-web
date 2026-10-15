import tailwindcss from '@tailwindcss/vite';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const API_URL = 'http://127.0.0.1:8765';

export default defineConfig({
	server: {
		// Proxy API requests to the backend during development.
		proxy: {
			'/api': {
				target: API_URL,
				changeOrigin: true,
			},
			'/auth': {
				target: API_URL,
				changeOrigin: true,
			},
			'/api/auth': {
				target: API_URL,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/auth/, ''),
			},
		}
	},
	define: {
		// Production builds use relative paths (empty string) so the
		// API calls go to the same origin that serves the static files.
		'__API_BASE__': process.env.NODE_ENV === 'production'
			? JSON.stringify('')
			: JSON.stringify(API_URL),
	},
	resolve: {
		alias: {
			'#lib': resolve(__dirname, './src/lib'),
		}
	},
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter({ fallback: 'index.html' })
		})
	]
});
