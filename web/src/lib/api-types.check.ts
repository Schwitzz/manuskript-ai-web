// Compile-time checks only (run by `npm run check`): wrong calls must NOT type-check.
import { call } from './api.ts';

export async function typed() {
const outline = await call('GET /api/projects/{name}/outline', { params: { name: 'acts' } });
const words: number = outline.words;
const first: string = outline.items[0].title;

await call('PUT /api/projects/{name}/documents/{item_id}', {
params: { name: 'acts', item_id: 12 },
body: { text: 'x', base_version: 'abc' }
});

// @ts-expect-error unknown route
await call('GET /api/nope');
// @ts-expect-error missing path parameter
await call('GET /api/projects/{name}/outline', {});
// @ts-expect-error body has the wrong shape
await call('PUT /api/projects/{name}/documents/{item_id}', { params: { name: 'a', item_id: 1 }, body: { text: 1 } });
// @ts-expect-error a GET takes no body
await call('GET /api/projects', { body: { x: 1 } });
return [words, first];
}
