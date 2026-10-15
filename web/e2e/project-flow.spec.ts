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
	await page.getByRole('button', { name: 'Scene', exact: true }).click();
	await page.getByLabel('Status').selectOption({ label: 'First draft' });
	await expect(page.getByRole('alert')).toHaveCount(0);
	const outline = await page.request.get('/api/projects/novel/outline');
	const chapter = (await outline.json()).items[0].children[0];
	expect(chapter.meta).toMatchObject({ label: '4', status: '2' });

	// Add a Note associated with the highlighted Chapter 1 and verify it shows up.
	await page.getByRole('button', { name: 'Add item' }).click();
	await expect(page.getByRole('button', { name: 'Add folder' })).toBeVisible();
	await expect(page.getByRole('button', { name: 'Add chapter' })).toBeVisible();
	await expect(page.getByRole('button', { name: 'Add scene' })).toBeVisible();
	await page.getByRole('button', { name: 'Add note' }).click();
	const dialog = page.getByRole('dialog', { name: 'Add note' });
	await dialog.getByLabel('Title').fill('Plot clue');
	await dialog.getByLabel('Note', { exact: true }).fill('The butler left a muddy footprint.');
	await dialog.getByRole('button', { name: 'Add note' }).click();
	await expect(page.getByText('Plot clue').first()).toBeVisible();
	await expect(page.getByText(/muddy footprint/).first()).toBeVisible();

	// Add a Chapter and then a Scene: the Scene indexes under the Chapter, not inline.
	await page.getByRole('button', { name: 'Add item' }).click();
	await page.getByRole('button', { name: 'Add chapter' }).click();
	const chDialog = page.getByRole('dialog', { name: 'Add chapter' });
	await chDialog.getByLabel('Title').fill('Chapter 2');
	await chDialog.getByRole('button', { name: 'Add chapter' }).click();
	await expect(page.getByRole('treeitem', { name: /Chapter 2/ })).toBeVisible();

	// With Chapter 2 selected, add a Scene and verify it nests inside Chapter 2.
	await page.getByRole('button', { name: 'Add item' }).click();
	await page.getByRole('button', { name: 'Add scene' }).click();
	const scDialog = page.getByRole('dialog', { name: 'Add scene' });
	await scDialog.getByLabel('Title').fill('Scene 2A');
	await scDialog.getByRole('button', { name: 'Add scene' }).click();
	await expect(page.getByRole('treeitem', { name: /Scene 2A/ })).toBeVisible();

	const treeAfter = (await (await page.request.get('/api/projects/novel/outline')).json()).items;
	const draftFolder = treeAfter[0];
	const ch2 = draftFolder.children.find((c: { title: string }) => c.title === 'Chapter 2');
	const sc2a = draftFolder.children.find((c: { title: string }) => c.title === 'Scene 2A');
	expect(ch2.type).toBe('md');
	expect(sc2a.type).toBe('md');
	// Scene 2A is placed right after Chapter 2 and visually indexed one level deeper (depth 2 under Chapter 2 at depth 1)
	await expect(page.locator(`[data-node="${ch2.id}"]`)).toHaveAttribute('data-depth', '1');
	await expect(page.locator(`[data-node="${sc2a.id}"]`)).toHaveAttribute('data-depth', '2');

	// Highlight Chapter 2 (a chapter folder) and add a note to it as well.
	await page.getByRole('treeitem', { name: /Chapter 2/ }).click();
	await page.getByRole('button', { name: 'Add item' }).click();
	await page.getByRole('button', { name: 'Add note' }).click();
	const chNoteDialog = page.getByRole('dialog', { name: 'Add note' });
	await chNoteDialog.getByLabel('Title').fill('Chapter arc');
	await chNoteDialog.getByLabel('Note', { exact: true }).fill('Rising tension across the chapter.');
	await chNoteDialog.getByRole('button', { name: 'Add note' }).click();
	await expect(page.getByText('Chapter arc').first()).toBeVisible();

	// Switch to Table view and click a row's name to select it into the bottom editing section.
	await page.getByTitle('Table view').click();
	await page.locator('.outline-row', { hasText: 'Scene 2A' }).click();
	await expect(page.locator('h3', { hasText: 'Scene 2A' })).toBeVisible();
	await page.getByLabel('Summary sentence').fill('The investigation begins.');
	await page.getByLabel('Summary sentence').blur();
	await page.getByTitle('Tree view').click();

	// ...and survive a reload.
	await page.reload();
	await page.getByRole('treeitem', { name: /Chapter 1/ }).click();
	await expect(page.getByRole('button', { name: 'Scene', exact: true })).toHaveAttribute('aria-pressed', 'true');
	await expect(page.getByLabel('Status')).toHaveValue('2');
	await expect(page.getByText('Plot clue').first()).toBeVisible();
	await page.screenshot({ path: `screenshots/outline-${info.project.name}.png` });

	// "Open in editor" lands on that scene with its text.
	await page.getByRole('button', { name: 'Open in editor' }).click();
	await expect(page).toHaveURL(/\/write\?scene=2/);
	await expect(page.locator('.cm-content')).toContainText('dark and stormy night');
});

test('whiteboard: add nodes to the canvas, link them, and keep them after a reload', async ({ page }) => {
	await page.addInitScript(() => localStorage.setItem('msk_project', 'novel'));
	await login(page);
	await nav(page, 'Board');

	// The toolbar and canvas hydrate on the client (SvelteFlow), so wait for a
	// toolbar control before touching the canvas.
	await expect(page.getByTitle('Add node')).toBeVisible({ timeout: 10_000 });

	// Drop two shapes from the add-node menu onto the canvas.
	await page.getByTitle('Add node').click();
	await page.getByRole('button', { name: 'Rectangle', exact: true }).click();
	await expect(page.locator('.svelte-flow__node')).toHaveCount(1);

	// Edit the shape's label, note, and color after adding to the board.
	await page.getByLabel('Shape label').fill('Protagonist');
	await page.getByLabel('Shape note').fill('Secretly the heir');
	await expect(page.locator('.svelte-flow__node').first()).toContainText('Protagonist');

	await page.getByTitle('Color').click();
	await page.getByRole('button', { name: 'Color Red' }).click();
	await expect(page.locator('.shape-node').first()).toHaveAttribute('data-color', '#ef4444');

	// Toggle "Show notes" selector so the note is visible unobtrusively.
	await page.getByTitle('Show notes').click();
	await page.waitForTimeout(200);
	await expect(page.locator('[role="note"]')).toContainText('Secretly the heir');

	await page.getByTitle('Add node').click();
	await page.getByRole('button', { name: 'Circle', exact: true }).click();
	await expect(page.locator('.svelte-flow__node')).toHaveCount(2);

	// Select a line style -> activates connection mode -> click node 1 then node 2 to draw edge.
	await page.getByTitle('Line style').click();
	await expect(page.getByRole('button', { name: 'Solid', exact: true })).toBeVisible();
	await expect(page.getByRole('button', { name: 'Dash', exact: true })).toBeVisible();
	await expect(page.getByRole('button', { name: 'Dot', exact: true })).toBeVisible();
	await page.getByRole('button', { name: 'Solid dashed', exact: true }).click();
	await expect(page.getByTitle('Line style')).toHaveAttribute('aria-pressed', 'true');

	// Click first node, then second node to draw the line.
	await page.locator('.svelte-flow__node').first().click();
	await page.locator('.svelte-flow__node').nth(1).click();

	const edgePath = page.locator('.svelte-flow__edge-path');
	await expect(edgePath).toHaveCount(1);
	await expect(edgePath).toHaveAttribute('stroke-dasharray', '12 4 2 4');

	// Select the rendered edge and verify all 4 line types + edge color render on the SVG path.
	await page.locator('.svelte-flow__edge').first().click({ force: true });

	await page.getByTitle('Color').click();
	await page.getByRole('button', { name: 'Color Emerald' }).click();
	await expect(edgePath).toHaveAttribute('data-color', '#22c55e');

	await page.getByTitle('Line style').click();
	await page.getByRole('button', { name: 'Dash', exact: true }).click();
	await expect(edgePath).toHaveAttribute('stroke-dasharray', '8 5');

	await page.getByTitle('Line style').click();
	await page.getByRole('button', { name: 'Dot', exact: true }).click();
	await expect(edgePath).toHaveAttribute('stroke-dasharray', '2 5');

	await page.getByTitle('Line style').click();
	await page.getByRole('button', { name: 'Solid', exact: true }).click();
	await expect(edgePath).not.toHaveAttribute('stroke-dasharray', /.+/);

	await page.getByTitle('Line style').click();
	await page.getByRole('button', { name: 'Solid dashed', exact: true }).click();
	await expect(edgePath).toHaveAttribute('stroke-dasharray', '12 4 2 4');

	// Verify the two nodes are present (second one is blank by design)
	await expect(page.locator('.svelte-flow__node').first()).toContainText('Protagonist');
	await expect(page.locator('.svelte-flow__node')).toHaveCount(2);

	// Create a second whiteboard for the project, add a note, then switch back to Main Board.
	await page.getByRole('button', { name: 'Whiteboards' }).click();
	await page.getByRole('button', { name: 'New whiteboard' }).click();
	await page.getByLabel('Board name').fill('Subplot Board');
	await page.getByRole('button', { name: 'Save board' }).click();
	await expect(page.getByRole('button', { name: 'Whiteboards' })).toContainText('Subplot Board');
	await expect(page.locator('.svelte-flow__node')).toHaveCount(0);

	await page.getByTitle('Add node').click();
	await page.getByRole('button', { name: 'Note', exact: true }).click();
	await expect(page.locator('.svelte-flow__node')).toHaveCount(1);

	// Switch back to Main Board
	await page.getByRole('button', { name: 'Whiteboards' }).click();
	await page.getByRole('button', { name: 'Main Board' }).click();
	await expect(page.locator('.svelte-flow__node')).toHaveCount(2);

	// Clear localStorage and reload to prove whiteboards persisted on the server in whiteboards.json!
	await page.evaluate(() => {
		localStorage.removeItem('msk_whiteboard_novel');
		localStorage.removeItem('msk_whiteboards_novel');
	});
	await page.reload();
	await expect(page.getByTitle('Add node')).toBeVisible({ timeout: 10_000 });
	await expect(page.locator('.svelte-flow__node')).toHaveCount(2);
	await expect(page.locator('.shape-node').first()).toHaveAttribute('data-color', '#ef4444');
	await expect(page.locator('.svelte-flow__edge-path')).toHaveCount(1);
	await expect(page.locator('.svelte-flow__edge-path')).toHaveAttribute('stroke-dasharray', '12 4 2 4');
	await expect(page.locator('.svelte-flow__edge-path')).toHaveAttribute('data-color', '#22c55e');
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
