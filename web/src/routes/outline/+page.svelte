<script lang="ts">
	import AppShell from '#lib/components/AppShell.svelte';
	import NoProject from '#lib/components/NoProject.svelte';
	import OutlineNode from '#lib/components/OutlineNode.svelte';
	import { project } from '#lib/stores/project.svelte.ts';
	import { call, ApiError } from '#lib/api';
	import {
		findItem,
		flatten,
		flattenWithDepth,
		isChapterItem,
		resolvePlacementForAdd,
		siblingDepthOffset,
		toItems,
		type AssociatedNote,
		type LabelDef,
		nameAt,
		labelColor,
		type OutlineItem
	} from '#lib/outline.ts';
	import type { NewItem } from '#lib/api-types.ts';
	import { computeFlatTableMove, moveItem, inSubtree, sameParentPosition } from '#lib/dnd.ts';
	import Sortable from 'sortablejs';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import {
		ListTree, Table2, Columns, SortAsc, SortDesc,
		Trash2, Folder, FileText, BookOpen, Plus, StickyNote, X, GripVertical
	} from '@lucide/svelte';

	const PROJECT = project.name ?? '';

	let outline = $state<OutlineItem[]>([]);
	let labels = $state<LabelDef[]>([]);
	let statusList = $state<string[]>([]);
	let expanded = new SvelteSet<string>();
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
	let addOpen = $state(false);
	let addingType = $state<'folder' | 'chapter' | 'scene' | 'note' | null>(null);
	let addingTitle = $state('');
	let addingNoteText = $state('');
	let addingTargetId = $state<number | null>(null);
	let addingParentId = $state<number | null>(null);
	let addingPosition = $state<number | null>(null);
	let addError = $state('');
	let addBusy = $state(false);

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

	const tableRows = $derived.by(() => {
		const rows = flattenWithDepth(outline, 0, labels);
		if (!sortCol) return rows;
		return [...rows].sort((a, b) => {
			const va = cellSortKey(a.item, sortCol!);
			const vb = cellSortKey(b.item, sortCol!);
			if (typeof va === 'number' && typeof vb === 'number') return sortDir === 'asc' ? va - vb : vb - va;
			return sortDir === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
		});
	});

	// ─── Inline editing ────────────────────────────────────────────────────────
	type EditField = 'summary_sentence';
	let editCell = $state<{ id: number; field: EditField } | null>(null);
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

	// ─── Drag-and-drop ─────────────────────────────────────────────────────────
	const instances: Sortable[] = [];

	function restoreDomNode(evt: Sortable.SortableEvent) {
		const ref = evt.from.children[evt.oldIndex ?? 0] ?? null;
		if (evt.item.parentNode !== evt.from || ref !== evt.item) {
			evt.from.insertBefore(evt.item, ref);
		}
	}

	function persistMove(id: number, toParent: number | null, position: number) {
		let next: OutlineItem[];
		try {
			next = moveItem(outline, id, toParent, position);
		} catch {
			void load();
			return;
		}
		outline = next;
		if (toParent !== null && !expanded.has(String(toParent))) {
			expanded.add(String(toParent));
		}
		call('POST /api/projects/{name}/outline/{item_id}/move', {
			params: { name: PROJECT, item_id: id },
			body: { parent_id: toParent, position }
		})
			.then(() => load())
			.catch(async (err) => {
				error = msg(err, 'Could not move');
				await load();
			});
	}

	$effect(() => {
		const mode = viewMode;
		const root = mode === 'tree' ? treeEl : tableEl;
		const o = outline;
		const e = expanded;
		const sorted = sortCol;
		if (!root) return;
		instances.forEach((s) => s.destroy());
		instances.length = 0;

		if (mode === 'tree') {
			const containers = [
				root,
				...root.querySelectorAll<HTMLElement>('.outline-children')
			].filter((el): el is HTMLElement => el.classList.contains('outline-children'));

			for (const el of containers) {
				instances.push(
					Sortable.create(el, {
						draggable: '[data-node]',
						group: 'outline',
						animation: 120,
						forceFallback: true,
						fallbackTolerance: 4,
						delay: 150,
						delayOnTouchOnly: true,
						touchStartThreshold: 5,
						filter: 'input, textarea, select, button',
						preventOnFilter: false,
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
							if (!Number.isNaN(dragId) && toParent !== null && inSubtree(o, dragId, toParent)) {
								return false;
							}
							const rel = evt.related ?? null;
							if (rel?.dataset.node) {
								const rid = Number(rel.dataset.node);
								const f = findItem(o, rid);
								if (f?.type === 'folder' && !e.has(String(rid))) e.add(String(rid));
							}
							return true;
						},
						onEnd(evt) {
							dragging = false;
							const id = Number(evt.item.dataset.node);
							const toParent = parentOf(evt.to);
							const fromParent = parentOf(evt.from);
							const to = evt.newDraggableIndex;
							const from = evt.oldDraggableIndex;
							restoreDomNode(evt);
							if (!Number.isFinite(id) || to === undefined || from === undefined) return;
							if (evt.to === evt.from && from === to) return;
							const position =
								evt.to === evt.from || fromParent === toParent
									? sameParentPosition(from, to)
									: to;
							persistMove(id, toParent, position);
						}
					})
				);
			}
		} else if (!sorted) {
			const rowsEl = root.querySelector<HTMLElement>('.outline-table-rows');
			if (rowsEl) {
				instances.push(
					Sortable.create(rowsEl, {
						draggable: '[data-node]',
						animation: 120,
						forceFallback: true,
						fallbackTolerance: 4,
						delay: 150,
						delayOnTouchOnly: true,
						touchStartThreshold: 5,
						filter: 'input, textarea, select, button',
						preventOnFilter: false,
						scroll: true,
						scrollSensitivity: 30,
						scrollSpeed: 15,
						ghostClass: 'dnd-ghost',
						chosenClass: 'dnd-chosen',
						dragClass: 'dnd-drag',
						onChoose: () => (dragging = true),
						onUnchoose: () => (dragging = false),
						onEnd(evt) {
							dragging = false;
							const id = Number(evt.item.dataset.node);
							const to = evt.newDraggableIndex;
							const from = evt.oldDraggableIndex;
							restoreDomNode(evt);
							if (!Number.isFinite(id) || to === undefined || from === undefined || from === to) {
								return;
							}
							const move = computeFlatTableMove(outline, id, to);
							if (!move) return;
							persistMove(id, move.toParent, move.position);
						}
					})
				);
			}
		}
	});
	$effect(() => () => { instances.forEach((s) => s.destroy()); instances.length = 0; });

	function parentOf(el: HTMLElement): number | null {
		const v = el.dataset.parent;
		return v ? Number(v) : null;
	}

	function expandAll(items: OutlineItem[]) {
		for (const n of items) {
			if (n.type === 'folder') {
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
			addingTargetId = null;
			const placement = resolvePlacementForAdd(outline, labels, type, active);
			addingParentId = placement.parentId;
			addingPosition = placement.position;
		}
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

	async function saveAssociatedNotes(node: OutlineItem, nextNotes: AssociatedNote[]) {
		const before = node.associated_notes;
		node.associated_notes = nextNotes;
		try {
			await call('PATCH /api/projects/{name}/outline/{item_id}/fields', {
				params: { name: PROJECT, item_id: node.id },
				body: { associated_notes: nextNotes.length ? JSON.stringify(nextNotes) : '' }
			});
		} catch (e) {
			node.associated_notes = before;
			error = msg(e, 'Could not save note');
		}
	}

	async function updateAssociatedNoteText(node: OutlineItem, noteId: string, text: string) {
		const trimmed = text.slice(0, 2000);
		const current = node.associated_notes.find((n) => n.id === noteId);
		if (!current || current.text === trimmed) return;
		const nextNotes = node.associated_notes.map((n) =>
			n.id === noteId ? { ...n, text: trimmed } : n
		);
		await saveAssociatedNotes(node, nextNotes);
	}

	async function deleteAssociatedNote(node: OutlineItem, noteId: string) {
		const nextNotes = node.associated_notes.filter((n) => n.id !== noteId);
		await saveAssociatedNotes(node, nextNotes);
	}

	function openInEditor(node: OutlineItem) {
		if (node.type === 'folder') return;
		goto(`/write?scene=${node.id}`);
	}

	// ─── Add outline item or associated note ──────────────────────────────────
	async function saveAddItem() {
		const title = addingTitle.trim();
		if (!title) {
			addError = 'Title is required';
			return;
		}
		addError = '';
		addBusy = true;
		try {
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
				if (addingNoteText.length > 2000) {
					addError = 'Note must be 2,000 characters or fewer';
					return;
				}
				const newNote: AssociatedNote = {
					id: `note_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
					title,
					text: addingNoteText.slice(0, 2000)
				};
				const nextNotes = [...(target.associated_notes ?? []), newNote];
				await call('PATCH /api/projects/{name}/outline/{item_id}/fields', {
					params: { name: PROJECT, item_id: target.id },
					body: { associated_notes: JSON.stringify(nextNotes) }
				});
				await load();
				const refreshed = findItem(outline, target.id);
				if (refreshed) select(refreshed);
				addingType = null;
				return;
			}

			// Folder -> 'folder'; Chapter and Scene -> 'md' (editable on the Write page)
			const apiType = addingType === 'folder' ? 'folder' : 'md';
			const item: NewItem = { title, type: apiType };
			if (addingParentId !== null) item.parent_id = addingParentId;
			if (addingPosition !== null) item.position = addingPosition;

			const created = await call('POST /api/projects/{name}/outline', {
				params: { name: PROJECT },
				body: item
			});

			// Tag Chapter or Scene with its matching label position if defined in the project
			if (addingType === 'chapter' || addingType === 'scene') {
				const idx = labels.findIndex((l) => l.name.toLowerCase() === addingType);
				if (idx >= 0) {
					await call('PATCH /api/projects/{name}/outline/{item_id}/fields', {
						params: { name: PROJECT, item_id: created.id },
						body: { label: String(idx + 1) }
					});
				}
			}

			await load();
			if (addingParentId !== null) {
				expanded.add(String(addingParentId));
			}
			if (apiType === 'folder') {
				expanded.add(String(created.id));
			}
			const createdNode = findItem(outline, created.id);
			if (createdNode) select(createdNode);
			addingType = null;
		} catch (e) {
			addError = msg(e, 'Could not add');
		} finally {
			addBusy = false;
		}
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

				<div class="flex items-center gap-1">
					<!-- Column picker -->
					<div class="relative">
						<button class="tap rounded p-1" title="Columns" type="button"
							onclick={() => (pickerOpen = !pickerOpen)}>
							<Columns size={18} />
						</button>
						{#if pickerOpen}
							<div class="absolute right-0 top-10 z-50 min-w-44 rounded-lg border p-2 shadow-lg"
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

					<!-- Add item menu -->
					<div class="relative">
						<button class="tap rounded p-1" title="Add scene" aria-label="Add item" type="button"
							onclick={() => (addOpen = !addOpen)}>
							<Plus size={18} />
						</button>
						{#if addOpen}
							<div class="absolute right-0 top-10 z-50 min-w-48 rounded-lg border p-2 shadow-lg"
								style="background:var(--surface); border-color:var(--border)">
								<button class="flex w-full items-center gap-2 rounded px-3 py-2 text-sm hover:bg-[color:var(--border)]"
									type="button" onclick={() => { openAddForm('folder'); addOpen = false; }}>
									<Folder size={16} /> Add folder
								</button>
								<button class="flex w-full items-center gap-2 rounded px-3 py-2 text-sm hover:bg-[color:var(--border)]"
									type="button" onclick={() => { openAddForm('chapter'); addOpen = false; }}>
									<BookOpen size={16} /> Add chapter
								</button>
								<button class="flex w-full items-center gap-2 rounded px-3 py-2 text-sm hover:bg-[color:var(--border)]"
									type="button" onclick={() => { openAddForm('scene'); addOpen = false; }}>
									<FileText size={16} /> Add scene
								</button>
								<button class="flex w-full items-center gap-2 rounded px-3 py-2 text-sm hover:bg-[color:var(--border)]"
									type="button" onclick={() => { openAddForm('note'); addOpen = false; }}>
									<StickyNote size={16} /> Add note
								</button>
							</div>
						{/if}
					</div>
				</div>
			</div>

			{#if outline.length === 0}
				<p class="py-12 text-center" style="color: var(--muted)">This project has no scenes yet.</p>
			{:else if viewMode === 'tree'}
				<!-- Tree view -->
				<div class="outline-children flex flex-col rounded-lg border" style="border-color: var(--border)"
					role="tree" aria-label="Outline" data-parent="" bind:this={treeEl}>
					{#each outline as item, idx (item.id)}
						<OutlineNode
							node={item} depthOffset={siblingDepthOffset(outline, idx, labels)}
							{expanded} {selectedId} {editingId} {editingTitle}
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
									role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter') onSort(col.key); }}
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
					<div class="outline-table-rows">
					{#each tableRows as { item, depth } (item.id)}
						<div
							class="outline-row flex items-center border-b transition-colors hover:bg-[color:var(--accent)]/5 select-none cursor-pointer"
							data-node={item.id}
							data-depth={depth}
							aria-selected={selectedId === item.id}
							role="row" tabindex="0" onclick={() => select(item)} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(item); } }}
							style="border-color: var(--border); background: {selectedId === item.id ? 'color-mix(in srgb, var(--accent) 18%, transparent)' : 'transparent'}"
						>
							{#each COLUMNS as col}
								{#if visibleCols.has(col.key)}
									<div
										class="outline-cell flex items-center gap-1 px-2 py-1.5 overflow-hidden shrink-0"
										style="width: {col.width}; {col.key === 'name' ? `padding-left: ${8 + depth * 20}px` : ''}"
										onclick={() => select(item)}
										ondblclick={(e) => {
											select(item);
											if (col.key === 'name') {
												e.stopPropagation();
												startEdit(item);
											} else if (col.key === 'summary') {
												e.stopPropagation();
												startEditCell(item, 'summary_sentence');
											}
										}}
										role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); e.preventDefault(); select(item); } }}
									>
										{#if col.key === 'name'}
											<span
												class="outline-drag-handle flex size-5 shrink-0 cursor-grab items-center justify-center opacity-60 hover:opacity-100 active:cursor-grabbing"
												title="Drag to reorder"
												aria-label="Drag {item.title}"
											>
												<GripVertical size={13} />
											</span>
											{#if item.type === 'folder'}
												<Folder size={14} style="color:var(--muted)" />
											{:else if isChapterItem(item, labels)}
												<BookOpen size={14} style="color:var(--muted)" />
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
												<span class="size-2.5 shrink-0 rounded-full" style="background:{labelColor(labels, item.label)}" aria-hidden="true"></span>
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
												></textarea>
											{:else}
												<span class="min-w-0 flex-1 truncate text-sm" style="color:var(--muted)">
													{item.summary_sentence || '—'}
												</span>
											{/if}
										{/if}
									</div>
								{/if}
							{/each}
						</div>
					{/each}
					</div>
				</div>
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

{#if addingType}
	<div class="add-form" role="dialog" aria-label="Add {addingType}">
		<div class="add-form-card">
			<div class="add-form-header">
				<h3 class="capitalize">Add {addingType}</h3>
				<button type="button" class="add-form-close" onclick={() => (addingType = null)} title="Close">
					<X size={18} />
				</button>
			</div>

			{#if addingType === 'note'}
				<label class="add-form-label" style="color: var(--muted); font-size: .8rem;">
					Associated chapter or scene
					<select
						aria-label="Associated chapter or scene"
						class="add-form-input"
						style="background: var(--surface); color: var(--text)"
						value={addingTargetId ?? ''}
						onchange={(e) => (addingTargetId = e.currentTarget.value ? Number(e.currentTarget.value) : null)}
					>
						{#if editableItems.length === 0}
							<option value="">No chapters or scenes available</option>
						{:else}
							{#each editableItems as item (item.id)}
								<option value={item.id}>{item.title}</option>
							{/each}
						{/if}
					</select>
				</label>
			{/if}

			<label class="add-form-label" style="color: var(--muted); font-size: .8rem;">
				Title
				<input
					type="text"
					aria-label="Title"
					class="add-form-input"
					bind:value={addingTitle}
					oninput={() => (addError = '')}
					onkeydown={(e) => {
						if (e.key === 'Enter' && addingType !== 'note') saveAddItem();
						if (e.key === 'Escape') addingType = null;
					}}
					placeholder={addingType === 'note' ? 'Note name' : 'Name'}
				/>
			</label>

			{#if addingType === 'note'}
				<label class="add-form-label" style="color: var(--muted); font-size: .8rem;">
					<span class="flex items-center justify-between">
						<span>Note (up to 2,000 characters)</span>
						<span>{addingNoteText.length} / 2000</span>
					</span>
					<textarea
						aria-label="Note"
						class="add-form-input"
						rows={4}
						maxlength={2000}
						bind:value={addingNoteText}
						oninput={() => (addError = '')}
						placeholder="Write your note..."
					></textarea>
				</label>
			{/if}

			<div class="add-form-actions">
				<button class="add-form-cancel" type="button"
					onclick={() => (addingType = null)}>Cancel</button>
				<button class="add-form-save capitalize" type="button"
					onclick={saveAddItem}
					disabled={addBusy}>
					Add {addingType}
				</button>
			</div>
			{#if addError}
				<p class="add-form-error" role="alert" style="color: var(--danger); font-size: .8rem;">{addError}</p>
			{/if}
		</div>
	</div>
{/if}

<style>
	/* ─── Drag-and-drop states ─────────────────────────────────────────────── */
	:global(.dnd-ghost) {
		opacity: 0.4;
		background: color-mix(in srgb, var(--accent) 15%, var(--surface)) !important;
	}
	:global(.dnd-chosen) {
		background: color-mix(in srgb, var(--accent) 12%, var(--surface));
	}
	:global(.dnd-drag) {
		opacity: 0.92;
		background: var(--surface);
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
		border-radius: 6px;
	}

	/* ─── Outline table ──────────────────────────────────────────────────────── */
	.outline-header {
		user-select: none;
		-webkit-user-select: none;
	}
	.outline-row { cursor: pointer; }

	/* Stacked rows on phone (narrow screens) */
	@media (max-width: 768px) {
		.outline-header { display: none; }
		.outline-row {
			flex-direction: column;
			align-items: stretch;
			gap: 0;
			border-radius: 0;
		}
		.outline-cell {
			flex-direction: row;
			width: auto !important;
			gap: 8px;
			padding: 6px 12px;
		}
	}

	/* ─── Add form overlay ─────────────────────────────────────────────────── */
	.add-form {
		position: fixed;
		inset: 0;
		z-index: 100;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(0,0,0,.5);
	}
	.add-form-card {
		width: min(90vw, 420px);
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: .75rem;
		padding: 1rem;
		box-shadow: 0 12px 40px rgba(0,0,0,.3);
	}
	.add-form-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1rem;
	}
	.add-form-header h3 {
		margin: 0;
		font-size: 1rem;
	}
	.add-form-close {
		background: none;
		border: none;
		color: var(--muted);
		cursor: pointer;
		padding: .25rem;
		border-radius: .375rem;
	}
	.add-form-close:hover { color: var(--text); background: var(--border); }
	.add-form-label {
		display: flex;
		flex-direction: column;
		gap: .5rem;
		margin-bottom: 1rem;
	}
	.add-form-input {
		width: 100%;
		padding: .75rem;
		border: 1px solid var(--border);
		border-radius: .5rem;
		background: transparent;
		color: var(--text);
		font-size: 1rem;
	}
	.add-form-input:focus { outline: 2px solid var(--accent); border-color: var(--accent); }
	.add-form-actions {
		display: flex;
		gap: .5rem;
	}
	.add-form-cancel {
		flex: 1;
		padding: .6rem;
		border: 1px solid var(--border);
		border-radius: .5rem;
		background: transparent;
		color: var(--text);
		cursor: pointer;
	}
	.add-form-save {
		flex: 1;
		padding: .6rem;
		border: none;
		border-radius: .5rem;
		background: var(--accent);
		color: var(--accent-text);
		font-weight: 600;
		cursor: pointer;
	}
	.add-form-save:hover { opacity: .9; }
	.add-form-save:disabled { opacity: .5; cursor: not-allowed; }
	.add-form-error { margin-top: .5rem; }
</style>
