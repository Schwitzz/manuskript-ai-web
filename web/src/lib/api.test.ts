import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, call } from './api.ts';

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);
vi.stubGlobal('document', { cookie: 'msk_csrf=tok%3D1; other=x' });
});
afterEach(() => vi.unstubAllGlobals());

const ok = (body: unknown, status = 200) =>
new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

describe('call', () => {
it('fills path parameters, encoding them', async () => {
fetchMock.mockResolvedValue(ok({ words: 1, chars: 2, title: 't', items: [] }));
await call('GET /api/projects/{name}/outline', { params: { name: 'My Novel/1' } });
expect(fetchMock.mock.calls[0][0]).toBe('/api/projects/My%20Novel%2F1/outline');
});

it('fills several parameters', async () => {
fetchMock.mockResolvedValue(ok({ version: 'v', words: 3 }));
await call('PUT /api/projects/{name}/documents/{item_id}', {
params: { name: 'acts', item_id: 12 },
body: { text: 'x', base_version: 'abc' }
});
const [url, init] = fetchMock.mock.calls[0];
expect(url).toBe('/api/projects/acts/documents/12');
expect(init.method).toBe('PUT');
expect(JSON.parse(init.body)).toEqual({ text: 'x', base_version: 'abc' });
});

it('sends the CSRF header on writes only', async () => {
fetchMock.mockResolvedValue(ok({ ok: true }));
await call('POST /api/auth/logout');
expect(fetchMock.mock.calls[0][1].headers['x-csrf-token']).toBe('tok=1');
fetchMock.mockResolvedValue(ok({ projects: [] }));
await call('GET /api/projects');
expect(fetchMock.mock.calls[1][1].headers['x-csrf-token']).toBeUndefined();
});

it('adds a query string', async () => {
fetchMock.mockResolvedValue(ok({ query: 'a b', truncated: false, results: [] }));
await call('GET /api/projects/{name}/search', {
params: { name: 'acts' },
query: { q: 'a b', case: true }
});
expect(fetchMock.mock.calls[0][0]).toBe('/api/projects/acts/search?q=a+b&case=true');
});

it('turns error responses into ApiError with status, message and Retry-After', async () => {
fetchMock.mockResolvedValue(
new Response(JSON.stringify({ detail: 'Too many attempts' }), {
status: 429,
headers: { 'content-type': 'application/json', 'retry-after': '30' }
})
);
const err = await call('POST /api/auth/login', { body: { username: 'a', password: 'b' } }).catch(
(e) => e
);
expect(err).toBeInstanceOf(ApiError);
expect(err).toMatchObject({ status: 429, message: 'Too many attempts', retryAfter: 30 });
});

it('keeps the 409 conflict payload reachable as a message', async () => {
fetchMock.mockResolvedValue(ok({ detail: { message: 'changed', version: 'v2', text: 't' } }, 409));
const err = await call('PUT /api/projects/{name}/documents/{item_id}', {
params: { name: 'a', item_id: 1 },
body: { text: 'x', base_version: 'old' }
}).catch((e) => e);
expect(err.status).toBe(409);
});
});
