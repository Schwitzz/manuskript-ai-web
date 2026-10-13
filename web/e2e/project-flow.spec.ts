import { test, expect, type Page } from '@playwright/test';

const PW = 'correct horse battery';

// Serial: the first test creates the only account, the rest build on its project.
test.describe.configure({ mode: 'serial' });

async function login(page: Page) {
	await page.goto('/login');
	await page.getByLabel('Username').fill('ab');
	await page.getByLabel(/Password/).fill(PW);
	await page.getByRole('button', { name: /Log in|Create account/ }).click();
	await expect(page).toHaveURL(/\/write/);
}

const nav = (page: Page, name: string) =>
	page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name }).click();

test('no project: every project page asks you to choose one instead of calling the API', async ({ page }) => {
	const apiCalls: string[] = [];
	page.on('request', (r) => {
		if (/\/api\/projects\/[^/]+\//.test(r.url())) apiCalls.push(r.url());
	});
	await login(page);
	await expect(page.getByText('No project selected')).toBeVisible();
	for (const route of ['outline', 'characters', 'plots', 'world', 'labels', 'settings']) {
		await page.goto(`/${route}`);
		await expect(page.getByRole('button', { name: 'Choose or create a project' })).toBeVisible();
	}
	expect(apiCalls).toEqual([]);
});

test('create a project, open it in the editor, and use the outline', async ({ page }, info) => {
	await login(page);
	await nav(page, 'More');
	await page.getByLabel('Name', { exact: true }).fill('novel');
	await page.getByRole('button', { name: 'Create Project' }).click();
	await page.getByRole('button', { name: 'novel' }).first().click();

	// Write opens the project's first real scene (a new project's scene id is 2, not 1).
	await expect(page).toHaveURL(/\/write/);
	await expect(page.getByText('Loading document')).toHaveCount(0);
	await expect(page.getByRole('alert')).toHaveCount(0);
	await expect(page.locator('.cm-content')).toBeVisible();
	await page.locator('.cm-content').click();
	await page.keyboard.type('It was a dark and stormy night.');
	await expect(page.getByText(/^Saved/)).toBeVisible({ timeout: 10_000 });

	// Outline shows the project, not a hardcoded one, with the typed scene in it.
	await nav(page, 'Outline');
	await expect(page.getByRole('treeitem', { name: /Chapter 1/ })).toBeVisible();

	// Label and status are stored as list positions (what desktop Manuskript reads).
	await page.getByRole('treeitem', { name: /Chapter 1/ }).click();
	await page.getByRole('button', { name: 'Scene' }).click();
	await page.getByLabel('Status').selectOption({ label: 'First draft' });
	await expect(page.getByRole('alert')).toHaveCount(0);
	const outline = await page.request.get('/api/projects/novel/outline');
	const chapter = (await outline.json()).items[0].children[0];
	expect(chapter.meta).toMatchObject({ label: '4', status: '2' });

	// ...and survive a reload.
	await page.reload();
	await page.getByRole('treeitem', { name: /Chapter 1/ }).click();
	await expect(page.getByRole('button', { name: 'Scene' })).toHaveAttribute('aria-pressed', 'true');
	await expect(page.getByLabel('Status')).toHaveValue('2');
	await page.screenshot({ path: `screenshots/outline-${info.project.name}.png` });

	// "Open in editor" lands on that scene with its text.
	await page.getByRole('button', { name: 'Open in editor' }).click();
	await expect(page).toHaveURL(/\/write\?scene=2/);
	await expect(page.locator('.cm-content')).toContainText('dark and stormy night');
});

test('corkboard: add scenes and the files follow', async ({ page }) => {
	await page.addInitScript(() => localStorage.setItem('msk_project', 'novel'));
	await login(page);
	await nav(page, 'Cards');

	// Page renders with an Add button; add a scene.
	await page.getByRole('button', { name: 'Add' }).click();
	await page.getByLabel('New item title').fill('Second');
	await page.getByRole('button', { name: 'Add', exact: true }).click();
	await expect(page.getByText('Second')).toBeVisible();

	// The server reflects the new scene.
	const items = (await (await page.request.get('/api/projects/novel/outline')).json()).items;
	expect(items[0].children.map((c: { title: string }) => c.title)).toContain('Second');
});

test('characters: create one in the UI, then undo a delete', async ({ page }) => {
	await page.addInitScript(() => localStorage.setItem('msk_project', 'novel'));
	const urls: string[] = [];
	page.on('request', (r) => { if (r.method() === 'POST' && r.url().includes('/characters')) urls.push(r.url()); });
	await login(page);
	await nav(page, 'Characters');
	await page.getByRole('button', { name: 'Add first character' }).click();
	await page.getByPlaceholder('Character name').fill('Silas');
	await page.getByRole('button', { name: /^Save/ }).click();
	await expect(page.getByText('Silas').first()).toBeVisible();
	// it reached the right project (a missing project name used to produce /projects/undefined/...)
	expect(urls[0]).toMatch(/\/api\/projects\/novel\/characters$/);
	const created = (await (await page.request.get('/api/projects/novel/characters')).json()).characters;
	expect(created.map((c: { name: string }) => c.name)).toEqual(['Silas']);

	// Delete lives in the character's detail form, so open the character first.
	await page.getByText('Silas').first().click();
	page.on('dialog', (d) => d.accept()); // the page asks to confirm the delete, twice
	await page.getByRole('button', { name: /Delete/ }).click();
	const count = async () =>
		(await (await page.request.get('/api/projects/novel/characters')).json()).characters.length;
	await expect(page.getByText('"Silas" deleted')).toBeVisible(); // the undo toast
	expect(await count()).toBe(0);
	await page.getByRole('button', { name: 'Undo' }).click();
	await expect.poll(count).toBe(1); // undo really re-created it on the server
});

test('rename in the outline saves once and the long line wraps in the editor', async ({ page }) => {
	// Each test gets a fresh browser context, so pick the project the previous test made.
	await page.addInitScript(() => localStorage.setItem('msk_project', 'novel'));
	await login(page);
	await nav(page, 'Outline');
	await page.getByRole('button', { name: 'Rename Chapter 1' }).click();
	await page.getByLabel('Title').fill('Opening');
	await page.keyboard.press('Enter');
	await expect(page.getByRole('treeitem', { name: /Opening/ })).toBeVisible();
	await expect(page.getByRole('alert')).toHaveCount(0);

	await page.getByRole('treeitem', { name: /Opening/ }).click();
	await page.getByRole('button', { name: 'Open in editor' }).click();
	await page.locator('.cm-content').click();
	await page.keyboard.press('Control+End');
	await page.keyboard.type(' ' + 'word '.repeat(200));
	const { scroll, client } = await page.locator('.cm-scroller').evaluate((el) => ({
		scroll: el.scrollWidth,
		client: el.clientWidth
	}));
	expect(scroll).toBeLessThanOrEqual(client + 1); // wrapped: nothing to scroll sideways
});
