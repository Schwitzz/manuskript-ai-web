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

function csrfToken(): string {
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
