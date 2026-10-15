# Chunk 4: Scenes Index Under Chapters, Not Inline

**Status:** ✅ Complete (Tests Passing — 138 unit + 18 E2E + 308 server)

## Scope & Context Budget
- **Files to read/edit:**
  1. `web/src/lib/outline.ts` (117 lines)
  2. `web/src/lib/outline.test.ts` (82 lines)
  3. `web/src/routes/outline/+page.svelte` (~1050 lines)
  4. `web/e2e/project-flow.spec.ts` (~180 lines)
- **Estimated token usage:** ~18k tokens (well under 70k limit).

## What This Chunk Implements
1. **Chapters act as containers (`type: 'folder'`) and Scenes index under Chapters:**
   - In Manuskript (`server/msklib/model.py` and `server/app/api/outline.py`), only items with `type: 'folder'` can contain child `OutlineItem`s (such as `0-Chapter_8/0-The_church_scattered.md` in `book-of-acts`).
   - Previously in `web/src/routes/outline/+page.svelte` line 449:
     `const apiType = addingType === 'folder' ? 'folder' : 'md';`
     This created Chapters as leaf `'md'` files, making it impossible to index Scenes under Chapters.
   - Now, when `addingType === 'chapter'`, `apiType` is `'folder'` (tagged with the `'Chapter'` label).
2. **Smart parent resolution (`resolveParentForAdd`) so Scenes always index under Chapters, not inline:**
   - Adds a pure helper `resolveParentForAdd(outline, labels, addingType, active)` in `web/src/lib/outline.ts` (with unit tests in `web/src/lib/outline.test.ts`):
     - When `addingType === 'scene'`:
       - If `active` is a folder/chapter (`active.type === 'folder'`), `parent_id` is `active.id` (the scene indexes directly inside the selected chapter).
       - If `active` is a scene inside a chapter/folder (`active.parent_id !== null`), `parent_id` is `active.parent_id` (the new scene indexes under the same chapter).
       - If no item is selected (`active === null`), and the outline has at least one folder/chapter, `parent_id` defaults to the last folder/chapter's `id` so scenes index under a chapter rather than floating inline at root.
     - When `addingType === 'chapter'`:
       - If `active` is a Chapter folder (`isChapterItem(active, labels)`), the new Chapter is placed as a sibling (`active.parent_id`) rather than nested inside the other chapter. If `active` is a Part/Act folder (not labeled `'Chapter'`), the new Chapter is placed inside that Part/Act folder (`parent_id = active.id`).
       - If `active` is a scene inside a Chapter folder, the new Chapter is placed at the Chapter's parent level (`parentFolder.parent_id`).
3. **Table / Stacked View Hierarchy Indentation:**
   - Table view iterates over `tableRows` which flattens the tree with `{ item, depth }` so scenes appear directly under their parent chapters with visual indentation (`padding-left: {8 + depth * 20}px` on the Name cell).

---

## Step-by-Step Line Edits

### 1. Edit `web/src/lib/outline.ts` (Lines 100–117)

Add `isChapterItem`, `flattenWithDepth`, and `resolveParentForAdd` at the bottom of `web/src/lib/outline.ts`:

**`oldString`:**
```ts
export function flatten(items: OutlineItem[]): OutlineItem[] {
	return items.flatMap((i) => [i, ...flatten(i.children)]);
}

/** The first scene (not folder) in reading order, or null for a project with no scenes. */
export function firstScene(items: OutlineItem[]): OutlineItem | null {
	return flatten(items).find((i) => i.type !== 'folder') ?? null;
}

/** Name of the label/status at a 1-based position, or '' when none or out of range. */
export function nameAt<T>(list: T[], index: string, pick: (t: T) => string): string {
	const n = Number(index);
	return n >= 1 && n <= list.length ? pick(list[n - 1]) : '';
}

export function labelColor(labels: LabelDef[], index: string): string {
	return nameAt(labels, index, (l) => l.color);
}
```

**`newString`:**
```ts
export function flatten(items: OutlineItem[]): OutlineItem[] {
	return items.flatMap((i) => [i, ...flatten(i.children)]);
}

export function flattenWithDepth(
	items: readonly OutlineItem[],
	depth = 0
): { item: OutlineItem; depth: number }[] {
	return items.flatMap((item) => [
		{ item, depth },
		...flattenWithDepth(item.children, depth + 1)
	]);
}

/** The first scene (not folder) in reading order, or null for a project with no scenes. */
export function firstScene(items: OutlineItem[]): OutlineItem | null {
	return flatten(items).find((i) => i.type !== 'folder') ?? null;
}

/** Name of the label/status at a 1-based position, or '' when none or out of range. */
export function nameAt<T>(list: T[], index: string, pick: (t: T) => string): string {
	const n = Number(index);
	return n >= 1 && n <= list.length ? pick(list[n - 1]) : '';
}

export function labelColor(labels: LabelDef[], index: string): string {
	return nameAt(labels, index, (l) => l.color);
}

export function isChapterItem(item: OutlineItem, labels: LabelDef[]): boolean {
	const lname = nameAt(labels, item.label, (l) => l.name).toLowerCase();
	return lname === 'chapter' || /^chapter\b/i.test(item.title);
}

/**
 * Determine the parent folder ID when adding a 'folder', 'chapter', or 'scene'
 * so that scenes always index under chapters rather than inline.
 */
export function resolveParentForAdd(
	outline: readonly OutlineItem[],
	labels: LabelDef[],
	addingType: 'folder' | 'chapter' | 'scene',
	active: OutlineItem | null
): number | null {
	if (addingType === 'scene') {
		if (active) {
			if (active.type === 'folder') return active.id;
			if (active.parent_id !== null) return active.parent_id;
		}
		// Fallback: last folder in reading order so scenes index under a chapter/folder if one exists
		const folders = flatten([...outline]).filter((i) => i.type === 'folder');
		return folders.length > 0 ? folders[folders.length - 1].id : null;
	}

	if (addingType === 'chapter') {
		if (!active) return null;
		if (active.type === 'folder') {
			// If the active folder is itself a Chapter, add the new Chapter as a sibling, not nested inside it
			if (isChapterItem(active, labels)) return active.parent_id;
			return active.id;
		}
		// Active is a scene: if its parent is a Chapter folder, add the new Chapter as a sibling of that Chapter
		if (active.parent_id !== null) {
			const parentFolder = findItem(outline, active.parent_id);
			if (parentFolder && isChapterItem(parentFolder, labels)) {
				return parentFolder.parent_id;
			}
			return active.parent_id;
		}
		return null;
	}

	// addingType === 'folder'
	if (active?.type === 'folder') return active.id;
	return active?.parent_id ?? null;
}
```

---

### 2. Edit `web/src/lib/outline.test.ts` (Lines 1–82)

Add unit tests for `resolveParentForAdd` and `flattenWithDepth`:

**`oldString`:**
```ts
import { firstScene, flatten, labelColor, nameAt, parseAssociatedNotes, pathTo, toItems } from './outline.ts';
```

**`newString`:**
```ts
import {
	firstScene,
	flatten,
	flattenWithDepth,
	labelColor,
	nameAt,
	parseAssociatedNotes,
	pathTo,
	resolveParentForAdd,
	toItems
} from './outline.ts';
```

And at the end of `web/src/lib/outline.test.ts`:

**`oldString`:**
```ts
	it('returns empty array on missing or invalid JSON', () => {
		expect(parseAssociatedNotes(undefined)).toEqual([]);
		expect(parseAssociatedNotes('not-json')).toEqual([]);
	});
});
```

**`newString`:**
```ts
	it('returns empty array on missing or invalid JSON', () => {
		expect(parseAssociatedNotes(undefined)).toEqual([]);
		expect(parseAssociatedNotes('not-json')).toEqual([]);
	});
});

describe('resolveParentForAdd & flattenWithDepth (scenes index under chapters)', () => {
	const labels = [
		{ name: 'Idea', color: '#ff0' },
		{ name: 'Note', color: '#0f0' },
		{ name: 'Chapter', color: '#00f' },
		{ name: 'Scene', color: '#f00' }
	];
	const chapterTree: OutlineItemOut[] = [
		{
			id: 10,
			title: 'Chapter 1',
			type: 'folder',
			words: 100,
			meta: { label: '3' },
			children: [
				{ id: 11, title: 'Scene 1', type: 'md', words: 100, meta: { label: '4' }, children: [] }
			]
		}
	];

	it('indexes a new scene under the selected chapter or the selected scene’s parent chapter', () => {
		const items = toItems(chapterTree);
		const ch1 = items[0];
		const sc1 = ch1.children[0];
		expect(resolveParentForAdd(items, labels, 'scene', ch1)).toBe(10);
		expect(resolveParentForAdd(items, labels, 'scene', sc1)).toBe(10);
		expect(resolveParentForAdd(items, labels, 'scene', null)).toBe(10);
	});

	it('places a new chapter as a sibling of an existing chapter rather than inside it', () => {
		const items = toItems(chapterTree);
		const ch1 = items[0];
		const sc1 = ch1.children[0];
		expect(resolveParentForAdd(items, labels, 'chapter', ch1)).toBeNull();
		expect(resolveParentForAdd(items, labels, 'chapter', sc1)).toBeNull();
	});

	it('flattens items with their nesting depth for the table view', () => {
		const items = toItems(chapterTree);
		expect(flattenWithDepth(items).map((r) => ({ id: r.item.id, depth: r.depth }))).toEqual([
			{ id: 10, depth: 0 },
			{ id: 11, depth: 1 }
		]);
	});
});
```

---

### 3. Edit `web/src/routes/outline/+page.svelte`

#### Edit 3a: Import `flattenWithDepth` and `resolveParentForAdd` in `web/src/routes/outline/+page.svelte` (Lines 7–18)

**`oldString`:**
```svelte
	import {
		findItem,
		flatten,
		firstScene,
		toItems,
		type AssociatedNote,
		type LabelDef,
		nameAt,
		labelColor,
		type OutlineItem
	} from '#lib/outline.ts';
```

**`newString`:**
```svelte
	import {
		findItem,
		flatten,
		flattenWithDepth,
		firstScene,
		resolveParentForAdd,
		toItems,
		type AssociatedNote,
		type LabelDef,
		nameAt,
		labelColor,
		type OutlineItem
	} from '#lib/outline.ts';
```

#### Edit 3b: Compute `tableRows` with depth so scenes appear indexed under chapters in Table view

**`oldString`:**
```svelte
	const sortedOutline = $derived(
		sortCol
			? [...outline].sort((a, b) => {
					const va = cellSortKey(a, sortCol!);
					const vb = cellSortKey(b, sortCol!);
					if (typeof va === 'number' && typeof vb === 'number') return sortDir === 'asc' ? va - vb : vb - va;
					return sortDir === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
			  })
			: outline
	);
```

**`newString`:**
```svelte
	const tableRows = $derived.by(() => {
		const rows = flattenWithDepth(outline);
		if (!sortCol) return rows;
		return [...rows].sort((a, b) => {
			const va = cellSortKey(a.item, sortCol!);
			const vb = cellSortKey(b.item, sortCol!);
			if (typeof va === 'number' && typeof vb === 'number') return sortDir === 'asc' ? va - vb : vb - va;
			return sortDir === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
		});
	});
```

#### Edit 3c: Update `openAddForm` and `saveAddItem` so Chapters are created as `'folder'` and Scenes index under Chapters

In `openAddForm`:

**`oldString`:**
```svelte
		} else {
			addingTargetId = null;
			if (active?.type === 'folder') {
				addingParentId = active.id;
			} else if (active && active.parent_id !== null) {
				addingParentId = active.parent_id;
			} else {
				addingParentId = null;
			}
			addingPosition = null;
		}
```

**`newString`:**
```svelte
		} else {
			addingTargetId = null;
			addingParentId = resolveParentForAdd(outline, labels, type, active);
			addingPosition = null;
		}
```

And in `saveAddItem`:

**`oldString`:**
```svelte
			// Folder -> 'folder'; Chapter and Scene -> 'md' (editable on the Write page)
			const apiType = addingType === 'folder' ? 'folder' : 'md';
			const item: NewItem = { title, type: apiType };
```

**`newString`:**
```svelte
			// Folder and Chapter -> 'folder' (so scenes index under chapters); Scene -> 'md'
			const apiType = addingType === 'scene' ? 'md' : 'folder';
			const item: NewItem = { title, type: apiType };
```

#### Edit 3d: Render `tableRows` with indentation for child scenes in Table view

**`oldString`:**
```svelte
					<!-- Rows -->
					{#each sortedOutline as item (item.id)}
						<div
							class="outline-row flex items-center border-b transition-colors hover:bg-[color:var(--accent)]/5"
							data-node={item.id}
							role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter') select(item); }}
							style="border-color: var(--border)"
						>
							{#each COLUMNS as col}
								{#if visibleCols.has(col.key)}
									<div
										class="outline-cell flex items-center gap-1 px-2 py-1.5 overflow-hidden shrink-0"
										style="width: {col.width}"
										onclick={(e) => {
											if (col.key === 'name') {
												e.stopPropagation();
												startEdit(item);
											} else if (col.key === 'summary') {
												e.stopPropagation();
												startEditCell(item, 'summary_sentence');
											}
										}}
										role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); e.preventDefault(); } }}
									>
										{#if col.key === 'name'}
											{#if item.type === 'folder'}
												<Folder size={14} style="color:var(--muted)" />
											{:else}
												<FileText size={14} style="color:var(--muted)" />
											{/if}
```

**`newString`:**
```svelte
					<!-- Rows -->
					{#each tableRows as { item, depth } (item.id)}
						<div
							class="outline-row flex items-center border-b transition-colors hover:bg-[color:var(--accent)]/5"
							data-node={item.id}
							data-depth={depth}
							role="button" tabindex="0" onclick={() => select(item)} onkeydown={(e) => { if (e.key === 'Enter') select(item); }}
							style="border-color: var(--border)"
						>
							{#each COLUMNS as col}
								{#if visibleCols.has(col.key)}
									<div
										class="outline-cell flex items-center gap-1 px-2 py-1.5 overflow-hidden shrink-0"
										style="width: {col.width}; {col.key === 'name' ? `padding-left: ${8 + depth * 20}px` : ''}"
										onclick={(e) => {
											if (col.key === 'name') {
												e.stopPropagation();
												startEdit(item);
											} else if (col.key === 'summary') {
												e.stopPropagation();
												startEditCell(item, 'summary_sentence');
											}
										}}
										role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); e.preventDefault(); } }}
									>
										{#if col.key === 'name'}
											{#if item.type === 'folder'}
												<Folder size={14} style="color:var(--muted)" />
											{:else}
												<FileText size={14} style="color:var(--muted)" />
											{/if}
```

---

## Verification & Testing Instructions for Chunk 4

1. Update `web/e2e/project-flow.spec.ts` in the `create a project, open it in the editor, and use the outline` test (around line 74) to verify:
   - Adding a new Chapter (`Chapter 2`), then adding a new Scene (`Scene 2A`) while `Chapter 2` is selected indexes `Scene 2A` **under** `Chapter 2` (in `Chapter 2`'s `children`), not inline at root.
   - Adding a note to the `Chapter 2` folder works and persists.

**`oldString` in `web/e2e/project-flow.spec.ts`:**
```ts
	// ...and survive a reload.
	await page.reload();
```

**`newString` in `web/e2e/project-flow.spec.ts`:**
```ts
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
	expect(ch2.type).toBe('folder');
	expect(ch2.children.map((c: { title: string }) => c.title)).toEqual(['Scene 2A']);

	// Highlight Chapter 2 (a chapter folder) and add a note to it as well.
	await page.getByRole('treeitem', { name: /Chapter 2/ }).click();
	await page.getByRole('button', { name: 'Add item' }).click();
	await page.getByRole('button', { name: 'Add note' }).click();
	const chNoteDialog = page.getByRole('dialog', { name: 'Add note' });
	await chNoteDialog.getByLabel('Title').fill('Chapter arc');
	await chNoteDialog.getByLabel('Note', { exact: true }).fill('Rising tension across the chapter.');
	await chNoteDialog.getByRole('button', { name: 'Add note' }).click();
	await expect(page.getByText('Chapter arc').first()).toBeVisible();

	// ...and survive a reload.
	await page.reload();
```

2. Run the full verification suite (server pytest, web vitest, svelte-check, build, and Playwright E2E):
   ```bash
   cd server && uv run pytest
   cd ../web && npm run check && npm test && npm run build && npx playwright test
   ```
3. **Update Markdown Files & Pause:**
   - Update `README.md`, `web/README.md`, `PLAN.md`, `features.md`, and `chunk-4-scenes-index-under-chapters.md` to mark Chunk 4 and the overall feature set as `✅ Complete (All Tests Passing)`.
   - **PAUSE HERE** and report final completion to the user.
