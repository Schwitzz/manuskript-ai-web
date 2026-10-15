# Chunk 3: Outline Stacked/Table View Note Removal & Notes on Both Chapters and Scenes

**Status:** ✅ Complete (Tests Passing — 138 unit + 18 E2E + 308 server)

## Scope & Context Budget
- **Files to read/edit:**
  1. `web/src/routes/outline/+page.svelte` (lines 45–165, 280–450, and 615–915)
- **Estimated token usage:** ~15k tokens (well under 70k limit).

## What This Chunk Implements
1. **Remove the `notes` column/field from Outline table / stacked view:**
   - Removes `{ key: 'notes', label: 'Notes', width: '200px' }` from `COLUMNS` in `web/src/routes/outline/+page.svelte`.
   - Removes `'notes'` from inline table cell editing (`EditField`, `cellText`, and the `{:else if col.key === 'notes'}` branch in the table row template).
   - Removes the standalone `<textarea>` for `Notes` in the bottom detail panel so that notes are exclusively added/managed by highlighting a chapter or scene and clicking **Add note** (from the `+` toolbar menu or the **New note** button in the detail panel).
2. **Ensure notes can be added to BOTH chapters and scenes:**
   - Previously, `editableItems`, `openAddForm('note')`, `saveAddItem()`, and the detail panel's `Associated notes` section had `item.type !== 'folder'` guards that blocked folder-type chapters from receiving notes.
   - Removes those `type !== 'folder'` restrictions so any chapter (whether `folder` or `md`) or scene can be highlighted (selected) and have notes added to it, displayed under it in the outline tree, and edited/deleted in the detail panel.

---

## Step-by-Step Line Edits

### 1. Edit `web/src/routes/outline/+page.svelte`

#### Edit 1a: Allow all outline items (chapters, folders, and scenes) in `editableItems` and remove `'notes'` from `COLUMNS` and inline table editing (Lines 55–130)

**`oldString`:**
```svelte
	const selected = $derived(selectedId === null ? null : findItem(outline, selectedId));
	const editableItems = $derived(flatten(outline).filter((i) => i.type !== 'folder'));

	// ─── View toggle ───────────────────────────────────────────────────────────
	let viewMode = $state<'tree' | 'table'>('tree');

	// ─── Column definitions ────────────────────────────────────────────────────
	interface ColDef {
		key: string;
		label: string;
		width: string;
	}
	const COLUMNS: ColDef[] = [
		{ key: 'name',    label: 'Name',    width: '220px' },
		{ key: 'words',   label: 'Words',   width: '60px' },
		{ key: 'label',   label: 'Label',   width: '80px' },
		{ key: 'status',  label: 'Status',  width: '80px' },
		{ key: 'compile', label: 'Compile', width: '50px' },
		{ key: 'pov',     label: 'POV',     width: '50px' },
		{ key: 'summary', label: 'Summary', width: '160px' },
		{ key: 'notes',   label: 'Notes',   width: '200px' }
	];
	let visibleCols = new SvelteSet(COLUMNS.map((c) => c.key));
	let pickerOpen = $state(false);

	function toggleCol(key: string) {
		if (visibleCols.has(key)) visibleCols.delete(key);
		else visibleCols.add(key);
		pickerOpen = false;
	}

	// ─── Sorting ───────────────────────────────────────────────────────────────
	let sortCol = $state<string | null>(null);
	let sortDir = $state<'asc' | 'desc'>('asc');

	function onSort(key: string) {
		if (sortCol === key) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
		else { sortCol = key; sortDir = 'asc'; }
	}

	function cellText(item: OutlineItem, key: string): string {
		switch (key) {
			case 'name':    return item.title;
			case 'words':   return String(item.words);
			case 'label':   return nameAt(labels, item.label, (l) => l.name);
			case 'status':  return nameAt(statusList, item.status, (s) => s);
			case 'compile': return item.compile;
			case 'pov':     return item.pov;
			case 'summary': return item.summary_sentence;
			case 'notes':   return item.notes;
			default:        return '';
		}
	}

	function cellSortKey(item: OutlineItem, key: string): string | number {
		switch (key) {
			case 'words': return item.words;
			default:      return cellText(item, key);
		}
	}

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

	// ─── Inline editing ────────────────────────────────────────────────────────
	type EditField = 'summary_sentence' | 'notes';
```

**`newString`:**
```svelte
	const selected = $derived(selectedId === null ? null : findItem(outline, selectedId));
	const editableItems = $derived(flatten(outline));

	// ─── View toggle ───────────────────────────────────────────────────────────
	let viewMode = $state<'tree' | 'table'>('tree');

	// ─── Column definitions ────────────────────────────────────────────────────
	interface ColDef {
		key: string;
		label: string;
		width: string;
	}
	const COLUMNS: ColDef[] = [
		{ key: 'name',    label: 'Name',    width: '220px' },
		{ key: 'words',   label: 'Words',   width: '60px' },
		{ key: 'label',   label: 'Label',   width: '80px' },
		{ key: 'status',  label: 'Status',  width: '80px' },
		{ key: 'compile', label: 'Compile', width: '50px' },
		{ key: 'pov',     label: 'POV',     width: '50px' },
		{ key: 'summary', label: 'Summary', width: '160px' }
	];
	let visibleCols = new SvelteSet(COLUMNS.map((c) => c.key));
	let pickerOpen = $state(false);

	function toggleCol(key: string) {
		if (visibleCols.has(key)) visibleCols.delete(key);
		else visibleCols.add(key);
		pickerOpen = false;
	}

	// ─── Sorting ───────────────────────────────────────────────────────────────
	let sortCol = $state<string | null>(null);
	let sortDir = $state<'asc' | 'desc'>('asc');

	function onSort(key: string) {
		if (sortCol === key) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
		else { sortCol = key; sortDir = 'asc'; }
	}

	function cellText(item: OutlineItem, key: string): string {
		switch (key) {
			case 'name':    return item.title;
			case 'words':   return String(item.words);
			case 'label':   return nameAt(labels, item.label, (l) => l.name);
			case 'status':  return nameAt(statusList, item.status, (s) => s);
			case 'compile': return item.compile;
			case 'pov':     return item.pov;
			case 'summary': return item.summary_sentence;
			default:        return '';
		}
	}

	function cellSortKey(item: OutlineItem, key: string): string | number {
		switch (key) {
			case 'words': return item.words;
			default:      return cellText(item, key);
		}
	}

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

	// ─── Inline editing ────────────────────────────────────────────────────────
	type EditField = 'summary_sentence';
```

#### Edit 1b: Allow `openAddForm('note')` and `saveAddItem()` to target any highlighted chapter or scene (Lines 282–430)

**`oldString`:**
```svelte
	function openAddForm(type: 'folder' | 'chapter' | 'scene' | 'note', targetNode?: OutlineItem) {
		addingType = type;
		addingTitle = '';
		addingNoteText = '';
		addError = '';
		const active = targetNode ?? selected;
		if (type === 'note') {
			if (active && active.type !== 'folder') {
				addingTargetId = active.id;
			} else if (active && active.type === 'folder') {
				const inner = firstScene(active.children);
				addingTargetId = inner?.id ?? firstScene(outline)?.id ?? null;
			} else {
				addingTargetId = firstScene(outline)?.id ?? null;
			}
			addingParentId = null;
			addingPosition = null;
		} else {
```

**`newString`:**
```svelte
	function openAddForm(type: 'folder' | 'chapter' | 'scene' | 'note', targetNode?: OutlineItem) {
		addingType = type;
		addingTitle = '';
		addingNoteText = '';
		addError = '';
		const active = targetNode ?? selected;
		if (type === 'note') {
			if (active) {
				addingTargetId = active.id;
			} else {
				addingTargetId = flatten(outline)[0]?.id ?? null;
			}
			addingParentId = null;
			addingPosition = null;
		} else {
```

And in `saveAddItem()`:

**`oldString`:**
```svelte
			if (addingType === 'note') {
				if (addingTargetId === null) {
					addError = 'Select or create a chapter or scene first';
					return;
				}
				const target = findItem(outline, addingTargetId);
				if (!target || target.type === 'folder') {
					addError = 'Notes must be associated with a chapter or scene';
					return;
				}
```

**`newString`:**
```svelte
			if (addingType === 'note') {
				if (addingTargetId === null) {
					addError = 'Select or create a chapter or scene first';
					return;
				}
				const target = findItem(outline, addingTargetId);
				if (!target) {
					addError = 'Notes must be associated with a chapter or scene';
					return;
				}
```

#### Edit 1c: Remove `notes` cell from the Table/Stacked view and update Detail Panel in `web/src/routes/outline/+page.svelte`

**`oldString`:**
```svelte
										onclick={(e) => {
											if (col.key === 'name' && item.type !== 'folder') {
												e.stopPropagation();
												startEdit(item);
											} else if (col.key === 'summary' || col.key === 'notes') {
												e.stopPropagation();
												startEditCell(item, col.key === 'summary' ? 'summary_sentence' : 'notes');
											}
										}}
```

**`newString`:**
```svelte
										onclick={(e) => {
											if (col.key === 'name') {
												e.stopPropagation();
												startEdit(item);
											} else if (col.key === 'summary') {
												e.stopPropagation();
												startEditCell(item, 'summary_sentence');
											}
										}}
```

And remove the `{:else if col.key === 'notes'}` block in the table row (around lines 700–724):

**`oldString`:**
```svelte
											{:else}
												<span class="min-w-0 flex-1 truncate text-sm" style="color:var(--muted)">
													{item.summary_sentence || '—'}
												</span>
											{/if}
										{:else if col.key === 'notes'}
											{#if item.type === 'folder'}
												<span class="text-xs" style="color:var(--muted)">—</span>
											{:else if editCell?.id === item.id && editCell.field === 'notes'}
												<textarea
													class="min-w-0 flex-1 rounded border px-1 py-0.5 text-sm"
													rows={2} style="background:var(--surface);border-color:var(--accent)"
													bind:value={editVal}
													onblur={() => saveEditCell(item.id, 'notes', editVal)}
													onkeydown={(e) => {
														e.stopPropagation();
														if (e.key === 'Enter' && !e.shiftKey) saveEditCell(item.id, 'notes', editVal);
														if (e.key === 'Escape') cancelEditCell();
													}}
													onclick={(e) => e.stopPropagation()}
													onfocus={(e) => {
														const ta = e.currentTarget; ta.select(); ta.scrollIntoView({ block: 'nearest' });
													}}
												></textarea>
											{:else}
												<span class="min-w-0 flex-1 truncate text-sm" style="color:var(--muted)">
													{item.notes || '—'}
												</span>
											{/if}
										{/if}
```

**`newString`:**
```svelte
											{:else}
												<span class="min-w-0 flex-1 truncate text-sm" style="color:var(--muted)">
													{item.summary_sentence || '—'}
												</span>
											{/if}
										{/if}
```

And in the Detail panel (around lines 790–857), remove the legacy `Notes` textarea and remove the `{#if selected.type !== 'folder'}` guard around `Associated notes` so both chapters (folders) and scenes show their associated notes and "+ New note" button:

**`oldString`:**
```svelte
					<label class="flex flex-col gap-1">
						<span class="text-xs" style="color: var(--muted)">Notes</span>
						<textarea
							class="w-full rounded border px-2 py-1 text-sm"
							rows={3}
							style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
							bind:value={draftNotes}
							onblur={() => setField(selected.id, 'notes', draftNotes)}
							placeholder="Scene notes"
						></textarea>
					</label>

					{#if selected.type !== 'folder'}
						<div class="flex flex-col gap-2">
							<div class="flex items-center justify-between">
								<span class="text-xs" style="color: var(--muted)">
									Associated notes ({selected.associated_notes?.length ?? 0})
								</span>
								<button
									type="button"
									class="flex items-center gap-1 rounded border px-2 py-1 text-xs"
									style="border-color: var(--border)"
									onclick={() => openAddForm('note', selected)}
								>
									<Plus size={12} /> New note
								</button>
							</div>

							{#if selected.associated_notes?.length}
								<div class="flex flex-col gap-2">
									{#each selected.associated_notes as note (note.id)}
										<div class="flex flex-col gap-1.5 rounded-lg border p-3" style="border-color: var(--border); background: var(--surface)">
											<div class="flex items-center justify-between gap-2">
												<div class="flex items-center gap-1.5 text-sm font-medium">
													<StickyNote size={14} style="color: var(--accent)" />
													<span>{note.title}</span>
												</div>
												<div class="flex items-center gap-2">
													<span class="text-xs" style="color: var(--muted)">{note.text.length}/2000</span>
													<button
														type="button"
														class="rounded p-1"
														style="color: var(--danger)"
														aria-label="Delete note {note.title}"
														onclick={() => deleteAssociatedNote(selected, note.id)}
													>
														<Trash2 size={14} />
													</button>
												</div>
											</div>
											<textarea
												class="w-full rounded border px-2 py-1 text-sm"
												rows={2}
												maxlength={2000}
												style="background: var(--bg); border-color: var(--border); color: var(--text); resize: vertical"
												value={note.text}
												onblur={(e) => updateAssociatedNoteText(selected, note.id, e.currentTarget.value)}
												placeholder="Note text (up to 2,000 characters)"
											></textarea>
										</div>
									{/each}
								</div>
							{:else}
								<p class="text-xs" style="color: var(--muted)">No associated notes yet.</p>
							{/if}
						</div>
					{/if}
```

**`newString`:**
```svelte
					<div class="flex flex-col gap-2">
						<div class="flex items-center justify-between">
							<span class="text-xs" style="color: var(--muted)">
								Associated notes ({selected.associated_notes?.length ?? 0})
							</span>
							<button
								type="button"
								class="flex items-center gap-1 rounded border px-2 py-1 text-xs"
								style="border-color: var(--border)"
								onclick={() => openAddForm('note', selected)}
							>
								<Plus size={12} /> New note
							</button>
						</div>

						{#if selected.associated_notes?.length}
							<div class="flex flex-col gap-2">
								{#each selected.associated_notes as note (note.id)}
									<div class="flex flex-col gap-1.5 rounded-lg border p-3" style="border-color: var(--border); background: var(--surface)">
										<div class="flex items-center justify-between gap-2">
											<div class="flex items-center gap-1.5 text-sm font-medium">
												<StickyNote size={14} style="color: var(--accent)" />
												<span>{note.title}</span>
											</div>
											<div class="flex items-center gap-2">
												<span class="text-xs" style="color: var(--muted)">{note.text.length}/2000</span>
												<button
													type="button"
													class="rounded p-1"
													style="color: var(--danger)"
													aria-label="Delete note {note.title}"
													onclick={() => deleteAssociatedNote(selected, note.id)}
												>
													<Trash2 size={14} />
												</button>
											</div>
										</div>
										<textarea
											class="w-full rounded border px-2 py-1 text-sm"
											rows={2}
											maxlength={2000}
											style="background: var(--bg); border-color: var(--border); color: var(--text); resize: vertical"
											value={note.text}
											onblur={(e) => updateAssociatedNoteText(selected, note.id, e.currentTarget.value)}
											placeholder="Note text (up to 2,000 characters)"
										></textarea>
									</div>
								{/each}
							</div>
						{:else}
							<p class="text-xs" style="color: var(--muted)">No associated notes yet.</p>
						{/if}
					</div>
```

---

## Verification & Testing Instructions for Chunk 3

1. Run TypeScript/Svelte check, unit tests, and E2E tests:
   ```bash
   cd web && npm run check && npm test && npm run build && npx playwright test e2e/project-flow.spec.ts
   ```
2. **Update Markdown Files & Pause:**
   - Update `README.md`, `web/README.md`, `PLAN.md`, `features.md`, and `chunk-3-outline-table-notes-and-chapter-notes.md` to mark Chunk 3 as `✅ Complete (Tests Passing)`.
   - **PAUSE HERE** and ask the user for permission to proceed to Chunk 4.
