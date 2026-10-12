<script lang="ts">
	import AppShell from '#lib/components/AppShell.svelte';
	import NoProject from '#lib/components/NoProject.svelte';
	import OutlineNode from '#lib/components/OutlineNode.svelte';
	import { project } from '#lib/stores/project.svelte.ts';
	import { call, ApiError } from '#lib/api';
	import { findItem, toItems, type LabelDef, nameAt, labelColor, type OutlineItem } from '#lib/outline.ts';
	import { moveItem, inSubtree, sameParentPosition } from '#lib/dnd.ts';
	import Sortable, { type SortableEvent, type MoveEvent } from 'sortablejs';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import {
		ListTree, Table2, Columns, SortAsc, SortDesc, GripVertical,
		Pencil, Trash2, ChevronDown, ChevronRight, Folder, FileText
	} from '@lucide/svelte';

	const PROJECT = project.name ?? '';

	let outline = $state<OutlineItem[]>([]);
	let labels = $state<LabelDef[]>([]);
	let statusList = $state<string[]>([]);
	let expanded = $state(new Set<string>());
	let loading = $state(true);
	let dragging = $state(false);
	let treeEl: HTMLDivElement | undefined = $state();
	let tableEl: HTMLDivElement | undefined = $state();
	let error = $state('');
	let editingId = $state<number | null>(null);
	let editingTitle = $state('');
	let selectedId = $state<number | null>(null);
	let draftSummary = $state('');
	let draftNotes = $state('');

	const selected = $derived(selectedId === null ? null : findItem(outline, selectedId));

	// ─── View toggle ───────────────────────────────────────────────────────────
	let viewMode = $state<'tree' | 'table'>('tree');

	// ─── Column definitions ────────────────────────────────────────────────────
	interface ColDef {
		key: string;
		label: string;
		width: string;
	}
	const COLUMNS: ColDef[] = [
		{ key: 'name',   label: 'Name',   width: '220px' },
		{ key: 'words',  label: 'Words',  width: '60px' },
		{ key: 'label',  label: 'Label',  width: '80px' },
		{ key: 'status', label: 'Status', width: '80px' },
		{ key: 'compile',label: 'Compile',width: '50px' },
		{ key: 'pov',    label: 'POV',    width: '50px' },
		{ key: 'summary',label: 'Summary',width: '160px' },
		{ key: 'notes',  label: 'Notes',  width: '200px' },
	];
	let visibleCols = $state(new Set(COLUMNS.map((c) => c.key)));
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
			case 'name':     return item.title;
			case 'words':    return String(item.words);
			case 'label':    return nameAt(labels, item.label, (l) => l.name);
			case 'status':   return nameAt(statusList, item.status, (s) => s);
			case 'compile':  return item.compile;
			case 'pov':      return item.pov;
			case 'summary':  return item.summary_sentence;
			case 'notes':    return item.notes;
			default:         return '';
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
	let editCell = $state<{id: number, field: EditField} | null>(null);
	let editVal = $state('');

	function startEditCell(item: OutlineItem, field: EditField) {
		if (item.type === 'folder') return;
		editCell = { id: item.id, field };
		editVal = item[field];
	}

	function cancelEditCell() {
		editCell = null;
		editVal = '';
	}

	async function saveEditCell(id: number, field: EditField, value: string) {
		if (editCell?.id !== id) return;
		const clean = value.trim();
		const node = findItem(outline, id);
		cancelEditCell();
		if (!node || !clean) return;
		const before = node[field];
		node[field] = clean;
		try {
			await call('PATCH /api/projects/{name}/outline/{item_id}/fields', {
				params: { name: PROJECT, item_id: id },
				body: { [field]: clean }
			});
		} catch (e) {
			node[field] = before;
			error = msg(e, 'Could not save');
		}
	}

	// ─── Drag-and-drop (existing) ──────────────────────────────────────────────
	const instances: Sortable[] = [];

	$effect(() => {
		const root = viewMode === 'tree' ? treeEl : tableEl;
		const o = outline; const e = expanded;
		if (!root) return;
		instances.forEach((s) => s.destroy());
		instances.length = 0;
		for (const el of root.querySelectorAll<HTMLElement>('.outline-children')) {
			instances.push(Sortable.create(el, {
				draggable: '[data-node]',
				group: 'outline',
				animation: 120,
				delay: 350,
				delayOnTouchOnly: true,
				touchStartThreshold: 5,
				scroll: true,
				scrollSensitivity: 30,
				scrollSpeed: 15,
				ghostClass: 'dnd-ghost',
				chosenClass: 'dnd-chosen',
				dragClass: 'dnd-drag',
				onChoose: () => (dragging = true),
				onUnchoose: () => (dragging = false),
				onMove(evt) {
					const dragId = Number(evt.dragged.dataset.node);
					const toParent = parentOf(evt.to);
					if (!Number.isNaN(dragId) && toParent !== null && inSubtree(o, dragId, toParent)) return false;
					const rel = evt.related ?? null;
					if (rel?.dataset.node) {
						const rid = Number(rel.dataset.node);
						const f = findItem(o, rid);
						if (f?.type === 'folder' && f.children.length > 0 && !e.has(String(rid))) e.add(String(rid));
					}
					return true;
				},
				onEnd(evt) {
					const id = Number(evt.item.dataset.node);
					if (!Number.isFinite(id)) return;
					const toParent = parentOf(evt.to);
					const fromParent = parentOf(evt.from);
					const to = evt.newDraggableIndex;
					const from = evt.oldDraggableIndex;
					if (to === undefined || from === undefined || evt.to === evt.from && from === to) return;
					const position = evt.to === evt.from || fromParent === toParent
						? sameParentPosition(from, to)
						: to;
					let next: OutlineItem[];
					try {
						next = moveItem(outline, id, toParent, position);
					} catch {
						void load();
						return;
					}
					outline = next;
					if (toParent !== null && !e.has(String(toParent))) e.add(String(toParent));
					call('POST /api/projects/{name}/outline/{item_id}/move', {
						params: { name: PROJECT, item_id: id },
						body: { parent_id: toParent, position }
					}).catch(async (e) => {
						error = msg(e, 'Could not move');
						await load();
					});
				}
			}));
		}
	});
	$effect(() => () => { instances.forEach((s) => s.destroy()); instances.length = 0; });

	function parentOf(el: HTMLElement): number | null {
		const v = el.dataset.parent;
		return v ? Number(v) : null;
	}

	function expandAll(items: OutlineItem[]) {
		for (const n of items) {
			if (n.children.length) {
				expanded.add(String(n.id));
				expandAll(n.children);
			}
		}
	}

	// ─── Load ──────────────────────────────────────────────────────────────────
	function msg(e: unknown, fallback: string): string {
		return e instanceof ApiError || e instanceof Error ? e.message : fallback;
	}

	async function load() {
		const [o, l] = await Promise.all([
			call('GET /api/projects/{name}/outline', { params: { name: PROJECT } }),
			call('GET /api/projects/{name}/labels', { params: { name: PROJECT } })
		]);
		outline = toItems(o.items);
		labels = l.labels;
		statusList = l.status;
	}

	onMount(async () => {
		if (!PROJECT) { loading = false; return; }
		try { await load(); expandAll(outline); }
		catch (e) { error = msg(e, 'Failed to load outline'); }
		finally { loading = false; }
	});

	// ─── Existing handlers ────────────────────────────────────────────────────
	function toggleExpand(id: number) {
		const key = String(id);
		if (expanded.has(key)) expanded.delete(key);
		else expanded.add(key);
	}

	function select(node: OutlineItem) {
		selectedId = node.id;
		draftSummary = node.summary_sentence;
		draftNotes = node.notes;
	}

	function startEdit(node: OutlineItem) {
		editingId = node.id;
		editingTitle = node.title;
	}

	function cancelEdit() {
		editingId = null;
		editingTitle = '';
	}

	async function renameItem(id: number, title: string) {
		if (editingId !== id) return;
		const clean = title.trim();
		const node = findItem(outline, id);
		cancelEdit();
		if (!clean || !node || clean === node.title) return;
		try {
			await call('PATCH /api/projects/{name}/outline/{item_id}/title', {
				params: { name: PROJECT, item_id: id },
				body: { title: clean }
			});
			node.title = clean;
		} catch (e) {
			error = msg(e, 'Could not rename');
		}
	}

	async function deleteItem(id: number) {
		const node = findItem(outline, id);
		if (!node) return;
		const what = node.children.length ? `"${node.title}" and everything inside it` : `"${node.title}"`;
		if (!confirm(`Move ${what} to the trash?`)) return;
		try {
			await call('DELETE /api/projects/{name}/outline/{item_id}', {
				params: { name: PROJECT, item_id: id }
			});
			await load();
			if (selectedId !== null && !findItem(outline, selectedId)) selectedId = null;
		} catch (e) {
			error = msg(e, 'Could not delete');
		}
	}

	type Field = 'label' | 'status' | 'summary_sentence' | 'notes';

	async function setField(id: number, field: Field, value: string) {
		const node = findItem(outline, id);
		if (!node || node[field] === value) return;
		const before = node[field];
		node[field] = value;
		try {
			await call('PATCH /api/projects/{name}/outline/{item_id}/fields', {
				params: { name: PROJECT, item_id: id },
				body: { [field]: value }
			});
		} catch (e) {
			node[field] = before;
			error = msg(e, 'Could not save');
		}
	}

	function openInEditor(node: OutlineItem) {
		if (node.type === 'folder') return;
		goto(`/write?scene=${node.id}`);
	}
</script>

<AppShell title="Outline">
	<div class="mx-auto flex max-w-4xl flex-col gap-4">
		{#if !PROJECT}
			<NoProject />
		{:else if loading}
			<p class="py-12 text-center" style="color: var(--muted)">Loading outline...</p>
		{:else}
			{#if error}
				<p role="alert" class="flex items-start gap-2" style="color: var(--danger)">
					<span class="flex-1">{error}</span>
					<button class="text-xs underline" type="button" onclick={() => (error = '')}>Dismiss</button>
				</p>
			{/if}

			{#if outline.length === 0}
				<p class="py-12 text-center" style="color: var(--muted)">This project has no scenes yet.</p>
			{:else}
				<!-- Toolbar -->
				<div class="flex items-center justify-between gap-2">
					<div class="flex items-center gap-1">
						<button class="tap rounded p-1" title="Tree view" type="button"
							onclick={() => (viewMode = 'tree')}>
							<ListTree size={18} style={viewMode === 'tree' ? 'color:var(--accent)' : ''} />
						</button>
						<button class="tap rounded p-1" title="Table view" type="button"
							onclick={() => (viewMode = 'table')}>
							<Table2 size={18} style={viewMode === 'table' ? 'color:var(--accent)' : ''} />
						</button>
					</div>

					<!-- Column picker -->
					<div class="relative">
						<button class="tap rounded p-1" title="Columns" type="button"
							onclick={() => (pickerOpen = !pickerOpen)}>
							<Columns size={18} />
						</button>
						{#if pickerOpen}
							<div class="absolute right-0 top-8 z-50 min-w-44 rounded-lg border p-2 shadow-lg"
								style="background:var(--surface); border-color:var(--border)">
								{#each COLUMNS as col}
									<label class="flex items-center gap-2 py-1 text-sm">
										<input type="checkbox" checked={visibleCols.has(col.key)}
											onchange={() => toggleCol(col.key)} />
										{col.label}
									</label>
								{/each}
							</div>
						{/if}
					</div>
				</div>

				<!-- Tree view -->
				{#if viewMode === 'tree'}
					<div class="flex flex-col rounded-lg border" style="border-color: var(--border)"
						role="tree" aria-label="Outline" bind:this={treeEl}>
						{#each outline as item (item.id)}
							<OutlineNode
								node={item} {expanded} {selectedId} {editingId} {editingTitle}
								{labels} {statusList}
								onToggleExpand={toggleExpand} onSelect={select}
								onRenameStart={startEdit} onRename={renameItem}
								onRenameCancel={cancelEdit} onDelete={deleteItem}
							/>
						{/each}
					</div>
				{:else}
					<!-- Table view -->
					<div
						class="rounded-lg border"
						style="border-color: var(--border)"
						bind:this={tableEl}
					>
						<!-- Header row -->
						<div class="outline-header flex items-center gap-0 border-b text-xs font-semibold"
							style="border-color: var(--border); color: var(--muted)">
							{#each COLUMNS as col}
								{#if visibleCols.has(col.key)}
									<div
										class="outline-col cursor-pointer px-2 py-1.5 select-none shrink-0"
										style="width: {col.width}"
										onclick={() => onSort(col.key)}
									>
										<span class="flex items-center gap-0.5">
											{col.label}
											{#if sortCol === col.key}
												{#if sortDir === 'asc'}<SortAsc size={12} />{:else}<SortDesc size={12} />{/if}
											{/if}
										</span>
									</div>
								{/if}
							{/each}
						</div>

						<!-- Rows -->
						{#each sortedOutline as item (item.id)}
							<div
								class="outline-row flex items-center border-b transition-colors hover:bg-[color:var(--accent)]/5"
								data-node={item.id}
								aria-selected={selectedId === item.id}
								style="border-color: var(--border)"
								onclick={() => select(item)}
							>
								{#each COLUMNS as col}
									{#if visibleCols.has(col.key)}
										<div
											class="outline-cell flex items-center gap-1 px-2 py-1.5 overflow-hidden shrink-0"
											style="width: {col.width}"
											onclick={(e) => {
												if (col.key === 'name' && item.type !== 'folder') {
													e.stopPropagation();
													startEdit(item);
												} else if (col.key === 'summary' || col.key === 'notes') {
													e.stopPropagation();
													startEditCell(item, col.key === 'summary' ? 'summary_sentence' : 'notes');
												}
											}}
										>
											{#if col.key === 'name'}
												{#if item.type === 'folder'}
													<Folder size={14} style="color:var(--muted)" />
												{:else}
													<FileText size={14} style="color:var(--muted)" />
												{/if}
												{#if editingId === item.id}
													<input
														class="min-w-0 flex-1 rounded border bg-transparent px-1 text-sm"
														style="border-color:var(--border)"
														aria-label="Title"
														bind:value={editingTitle}
														onblur={() => renameItem(item.id, editingTitle)}
														onkeydown={(e) => {
															e.stopPropagation();
															if (e.key === 'Enter') renameItem(item.id, editingTitle);
															if (e.key === 'Escape') cancelEdit();
														}}
														onclick={(e) => e.stopPropagation()}
													/>
												{:else}
													<span class="min-w-0 flex-1 truncate text-sm">{item.title}</span>
												{/if}
											{:else if col.key === 'words'}
												<span class="text-xs" style="color:var(--muted)">{item.words}</span>
											{:else if col.key === 'label'}
												{#if item.label}
													<span class="size-2.5 shrink-0 rounded-full" style="background:{labelColor(labels, item.label)}" aria-hidden></span>
													<span class="text-xs" style="color:var(--muted)">{nameAt(labels, item.label, (l) => l.name)}</span>
												{:else}
													<span class="text-xs" style="color:var(--muted)">—</span>
												{/if}
											{:else if col.key === 'status'}
												{#if item.status}
													<span class="text-xs" style="color:var(--muted)">{nameAt(statusList, item.status, (s) => s)}</span>
												{:else}
													<span class="text-xs" style="color:var(--muted)">—</span>
												{/if}
											{:else if col.key === 'compile'}
												{#if item.compile === '2'}
													<span class="text-xs" style="color:var(--muted)">✓</span>
												{:else}
													<span class="text-xs" style="color:var(--muted)">—</span>
												{/if}
											{:else if col.key === 'pov'}
												<span class="text-xs" style="color:var(--muted)">{item.pov}</span>
											{:else if col.key === 'summary'}
												{#if item.type === 'folder'}
													<span class="text-xs" style="color:var(--muted)">—</span>
												{:else if editCell?.id === item.id && editCell.field === 'summary_sentence'}
													<textarea
														class="min-w-0 flex-1 rounded border px-1 py-0.5 text-sm"
														rows={2} style="background:var(--surface);border-color:var(--accent)"
														bind:value={editVal}
														onblur={() => saveEditCell(item.id, 'summary_sentence', editVal)}
														onkeydown={(e) => {
															e.stopPropagation();
															if (e.key === 'Enter' && !e.shiftKey) saveEditCell(item.id, 'summary_sentence', editVal);
															if (e.key === 'Escape') cancelEditCell();
														}}
														onclick={(e) => e.stopPropagation()}
													/>
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
															const ta = e.currentTarget; ta.select(); ta.scrollIntoView({block:'nearest'});
														}}
													/>
												{:else}
													<span class="min-w-0 flex-1 truncate text-sm" style="color:var(--muted)">
														{item.notes || '—'}
													</span>
												{/if}
											{/if}
										</div>
									{/if}
								{/each}
							</div>
						{/each}
					</div>
				{/if}
			{/if}

			<!-- Detail panel (always below) -->
			{#if selected}
				<div class="flex flex-col gap-3 rounded-lg border p-4" style="border-color: var(--border)">
					<h3 class="font-medium">{selected.title}</h3>

					<div class="flex flex-col gap-1">
						<span class="text-xs" style="color: var(--muted)">Label</span>
						<div class="flex flex-wrap gap-1" role="group" aria-label="Label">
							<button
								type="button"
								class="rounded border px-2 py-1 text-xs"
								style="border-color: {selected.label === '' ? 'var(--accent)' : 'var(--border)'}"
								aria-pressed={selected.label === ''}
								onclick={() => setField(selected.id, 'label', '')}>None</button
							>
							{#each labels as l, i}
								<button
									type="button"
									class="flex items-center gap-1 rounded border px-2 py-1 text-xs"
									style="border-color: {selected.label === String(i + 1) ? 'var(--accent)' : 'var(--border)'}"
									aria-pressed={selected.label === String(i + 1)}
									onclick={() => setField(selected.id, 'label', String(i + 1))}
								>
									<span class="size-2.5 rounded-full" style="background: {l.color}"></span>
									{l.name}
								</button>
							{/each}
						</div>
					</div>

					<label class="flex flex-col gap-1">
						<span class="text-xs" style="color: var(--muted)">Status</span>
						<select
							class="rounded border px-2 py-1 text-sm"
							style="background: var(--surface); border-color: var(--border); color: var(--text)"
							value={selected.status}
							onchange={(e) => setField(selected.id, 'status', e.currentTarget.value)}
						>
							<option value="">None</option>
							{#each statusList as s, i}
								<option value={String(i + 1)}>{s}</option>
							{/each}
						</select>
					</label>

					<label class="flex flex-col gap-1">
						<span class="text-xs" style="color: var(--muted)">Summary sentence</span>
						<textarea
							class="w-full rounded border px-2 py-1 text-sm"
							rows={2}
							style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
							bind:value={draftSummary}
							onblur={() => setField(selected.id, 'summary_sentence', draftSummary)}
							placeholder="One-sentence summary of this scene"
						></textarea>
					</label>

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

					<div class="flex gap-2">
						{#if selected.type !== 'folder'}
							<button
								type="button"
								class="flex-1 rounded-lg px-3 py-2 text-sm font-medium"
								style="background: var(--accent); color: var(--accent-text)"
								onclick={() => openInEditor(selected)}>Open in editor</button
							>
						{/if}
						<button
							type="button"
							class="rounded-lg border px-3 py-2 text-sm"
							style="border-color: var(--border)"
							onclick={() => (selectedId = null)}>Close</button
						>
					</div>
				</div>
			{/if}
		{/if}
	</div>
</AppShell>

<style>
	/* ─── Outline table ──────────────────────────────────────────────────────── */
	.outline-header {
		user-select: none;
		-webkit-user-select: none;
	}
	.outline-row { cursor: default; }
	.outline-row:hover { cursor: pointer; }
	.outline-row[aria-selected] { background: var(--accent); color: var(--accent-text); }
	.outline-row[aria-selected] span[style*="--muted"],
	.outline-row[aria-selected] span[style*="var(--muted)"] { color: var(--accent-text) !important; opacity: .8; }

	/* Stacked rows on phone (narrow screens) */
	@media (max-width: 768px) {
		.outline-header { display: none; }
		.outline-row {
			flex-direction: column;
			align-items: stretch;
			gap: 0;
			border-radius: 0;
			border-bottom-width: 0;
		}
		.outline-cell {
			flex-direction: row;
			width: auto !important;
			gap: 8px;
			padding: 6px 12px;
			border-bottom: 1px solid var(--border);
		}
		.outline-cell > span:first-child,
		.outline-cell > button:first-child,
		.outline-cell > input:first-child,
		.outline-cell > textarea:first-child {
			font-weight: 600;
			min-width: 80px;
			color: var(--muted);
			flex-shrink: 0;
		}
		/* Hide the icon in the name cell on phone; keep label/status/summary/notes */
		.outline-cell:nth-of-type(1) { padding-left: 12px; }
		.outline-cell:nth-of-type(1) > span:first-child { display: none; }
		.outline-row:last-child { border-bottom: none; }
	}
</style>
