/** Minimal API client: JSON in/out, CSRF header from the readable cookie. */

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string,
		public retryAfter?: number
	) {
		super(message);
	}
}

export function csrfToken(): string {
	const m = document.cookie.match(/(?:^|;\s*)msk_csrf=([^;]+)/);
	return m ? decodeURIComponent(m[1]) : '';
}

export async function api<T = unknown>(method: string, path: string, body?: unknown): Promise<T> {
	const headers: Record<string, string> = {};
	if (body !== undefined) headers['content-type'] = 'application/json';
	if (method !== 'GET') headers['x-csrf-token'] = csrfToken();
	const res = await fetch(path, {
		method,
		headers,
		credentials: 'same-origin',
		body: body === undefined ? undefined : JSON.stringify(body)
	});
	if (!res.ok) {
		let msg = res.statusText;
		try {
			const j = await res.json();
			msg = typeof j.detail === 'string' ? j.detail : msg;
		} catch {
			/* keep statusText */
		}
		const ra = res.headers.get('retry-after');
		throw new ApiError(res.status, msg, ra ? Number(ra) : undefined);
	}
	return (await res.json()) as T;
}

export interface AuthStatus {
	setup_required: boolean;
	authenticated: boolean;
	totp_pending: boolean;
}

import type { Routes } from './api-types.ts';

type RouteKey = keyof Routes;
type ParamsOf<K extends string> = K extends `${string}{${infer P}}${infer Rest}`
? P | ParamsOf<Rest>
: never;

/**
 * Typed call: the route string, its path parameters, the request body and the response are
 * all checked against the server's OpenAPI schema.
 *   await call('GET /api/projects/{name}/outline', { params: { name: 'acts' } })
 */
export async function call<K extends RouteKey>(
route: K,
opts: (Routes[K]['body'] extends never ? { body?: never } : { body: Routes[K]['body'] }) &
(ParamsOf<K> extends never
? { params?: never }
: { params: Record<ParamsOf<K>, string | number> }) &
{ query?: Record<string, string | number | boolean> } = {} as never
): Promise<Routes[K]['response']> {
const [method, template] = (route as string).split(' ');
const o = opts as { body?: unknown; params?: Record<string, string | number>; query?: Record<string, string | number | boolean> };
let path = template.replace(/\{(\w+)\}/g, (_m, k: string) => encodeURIComponent(String(o.params?.[k])));
if (o.query) {
const qs = new URLSearchParams(Object.entries(o.query).map(([k, v]) => [k, String(v)]));
path += '?' + qs.toString();
}
return api(method, path, o.body) as Promise<Routes[K]['response']>;
}
