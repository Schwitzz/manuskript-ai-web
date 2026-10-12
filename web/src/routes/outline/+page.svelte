<script lang="ts">
	import AppShell from '#lib/components/AppShell.svelte';
	import NoProject from '#lib/components/NoProject.svelte';
	import OutlineNode from '#lib/components/OutlineNode.svelte';
	import { project } from '#lib/stores/project.svelte.ts';
	import { call, ApiError } from '#lib/api';
	import { findItem, toItems, type LabelDef, type OutlineItem } from '#lib/outline.ts';
	import { moveItem, inSubtree, sameParentPosition } from '#lib/dnd.ts';
	import Sortable, { type SortableEvent, type MoveEvent } from 'sortablejs';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	const PROJECT = project.name ?? '';

	let outline = $state<OutlineItem[]>([]);
	let labels = $state<LabelDef[]>([]);
	let statusList = $state<string[]>([]);
	let expanded = $state(new Set<string>());
	let loading = $state(true);
	let dragging = $state(false);
	let treeEl: HTMLDivElement | undefined = $state();
	let error = $state('');
	let editingId = $state<number | null>(null);
	let editingTitle = $state('');
	let selectedId = $state<number | null>(null);
	let draftSummary = $state('');
	let draftNotes = $state('');

	const selected = $derived(selectedId === null ? null : findItem(outline, selectedId));

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

	/**
	 * SortableJS on every `.outline-children` container.
	 * `outline` and `expanded` are dependencies — whenever the tree
	 * structure or open-folders change we (re)create the instances.
	 */
	const instances: Sortable[] = [];
	$effect(() => {
		const root = treeEl; const o = outline; const e = expanded;
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
					// Refuse dropping a folder into its own subtree.
					const dragId = Number(evt.dragged.dataset.node);
					const toParent = parentOf(evt.to);
					if (!Number.isNaN(dragId) && toParent !== null && inSubtree(o, dragId, toParent)) return false;
					// Hover over a collapsed folder → expand it so the user can drop into it.
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
					if (to === undefined || evt.to === evt.from && from === to) return;
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

	onMount(async () => {
		if (!PROJECT) {
			loading = false;
			return;
		}
		try {
			await load();
			expandAll(outline);
		} catch (e) {
			error = msg(e, 'Failed to load outline');
		} finally {
			loading = false;
		}
	});

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
		// Enter and the blur it causes can both land here; the first one clears editingId.
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
		node[field] = value; // optimistic; rolled back if the server refuses
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
	<div class="mx-auto flex max-w-2xl flex-col gap-4">
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
				<div class="flex flex-col rounded-lg border" style="border-color: var(--border)" role="tree" aria-label="Outline" bind:this={treeEl}>
					{#each outline as item (item.id)}
						<OutlineNode
							node={item}
							{expanded}
							{selectedId}
							{editingId}
							{editingTitle}
							{labels}
							{statusList}
							onToggleExpand={toggleExpand}
							onSelect={select}
							onRenameStart={startEdit}
							onRename={renameItem}
							onRenameCancel={cancelEdit}
							onDelete={deleteItem}
						/>
					{/each}
				</div>
			{/if}

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
