import { test, expect } from '@playwright/test';

// A LIVE test: it talks to a real llama.cpp server. It is skipped unless MSK_LLAMA_URL is set,
// so the normal suite never depends on a model being available.
//   MSK_LLAMA_URL=http://10.0.0.80:8180 MSK_LLAMA_MODEL=Qwen3.5-9B-UD-Q4_K_XL.gguf npx playwright test ai-live
const LLAMA = process.env.MSK_LLAMA_URL;
const MODEL = process.env.MSK_LLAMA_MODEL ?? 'Qwen3.5-9B-UD-Q4_K_XL.gguf';
const PW = 'correct horse battery';

test.skip(!LLAMA, 'set MSK_LLAMA_URL to run the live AI test');
test.describe.configure({ mode: 'serial' });

test('chat panel: the model answers using the open scene, and the chat is saved', async ({ page }) => {
	test.setTimeout(240_000);
	await page.goto('/login');
	await page.getByLabel('Username').fill('ab');
	await page.getByLabel(/Password/).fill(PW);
	await page.getByRole('button', { name: /Log in|Create account/ }).click();
	await expect(page).toHaveURL(/\/write/);

	// A project from the sample, with a made-up fact in one scene's summary that no model can know.
	const csrf = async () => (await page.context().cookies()).find((c) => c.name === 'msk_csrf')!.value;
	const post = async (url: string, data: unknown, method = 'POST') =>
		page.request.fetch(url, { method, data, headers: { 'x-csrf-token': await csrf() } });
	expect((await post('/api/projects', { name: 'acts', sample: 'book-of-acts' })).status()).toBe(201);
	const items = (await (await page.request.get('/api/projects/acts/outline')).json()).items;
	const flat = (xs: any[]): any[] => xs.flatMap((x) => [x, ...flat(x.children)]);
	const scene = flat(items).find((i) => i.title === 'Peter preaches');
	await post(`/api/projects/acts/outline/${scene.id}/fields`, {
		summary_sentence: 'The secret password of this scene is ZEBRA-4471.'
	}, 'PATCH');
	await post('/api/ai/providers', { settings: [{ provider: 'Local / Llama.cpp', endpoint: LLAMA, model: MODEL }] });

	await page.addInitScript(() => localStorage.setItem('msk_project', 'acts'));
	await page.goto(`/write?scene=${scene.id}`);
	await expect(page.locator('.cm-content')).toBeVisible();

	// Open the assistant, choose the local provider and model, and ask.
	await page.getByRole('button', { name: 'AI Chat' }).first().click();
	const panel = page.getByRole('textbox', { name: /Message/ });
	await expect(panel).toBeVisible();
	await page.locator('select').filter({ hasText: 'Local / Llama.cpp' }).selectOption('Local / Llama.cpp');
	await expect(page.locator('select').filter({ hasText: MODEL })).toBeVisible({ timeout: 20_000 });
	await page.locator('select').filter({ hasText: MODEL }).selectOption(MODEL);

	await panel.fill('Quote the Scene summary section of your context back to me exactly.');
	await panel.press('Enter');

	// It streams (the status line shows while it works), then the answer appears.
	await expect(page.getByText('ZEBRA-4471').last()).toBeVisible({ timeout: 180_000 });
	await expect(page.getByRole('alert')).toHaveCount(0);

	// The turn was saved: one user message and one assistant message.
	await expect.poll(async () => {
		const chats = (await (await page.request.get('/api/ai/chats')).json()).chats;
		if (!chats.length) return 0;
		return (await (await page.request.get(`/api/ai/chats/${chats[0].id}`)).json()).messages.length;
	}, { timeout: 15_000 }).toBe(2);
});
