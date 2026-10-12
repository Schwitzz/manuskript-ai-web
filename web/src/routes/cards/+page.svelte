<script lang="ts">
	import AppShell from '#lib/components/AppShell.svelte';
	import NoProject from '#lib/components/NoProject.svelte';
	import { project } from '#lib/stores/project.svelte.ts';
	import { call, ApiError } from '#lib/api';
	import { findItem, labelColor, pathTo, toItems, type LabelDef, type OutlineItem } from '#lib/outline.ts';
	import { moveItem, sameParentPosition } from '#lib/dnd.ts';
	import Sortable from 'sortablejs';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { ChevronLeft, ChevronRight, ChevronUp, Folder, FileText, Plus, LayoutGrid, Waypoints } from '@lucide/svelte';
	import Whiteboard from '#lib/components/Whiteboard.svelte';

	const PROJECT = project.name ?? '';

	let outline = $state<OutlineItem[]>([]);
	let labels = $state<LabelDef[]>([]);
	let statusList = $state<string[]>([]);
	let loading = $state(true);
	let error = $state('');
	/** The folder being shown; null = the top level. */
	let folderId = $state<number | null>(null);
	let adding = $state(false);
	let newTitle = $state('');
	let busy = $state(false);
	/** View mode: 'grid' (card list) or 'flow' (whiteboard). */
	let view = $state<'grid' | 'flow'>('grid');
	/** True while a card is being lifted/dragged; disables the arrow buttons. */
	let dragging = $state(false);
	/** The grid element, so the sortable can follow it across view toggles. */
	let gridEl: HTMLUListElement | undefined = $state();

	const trail = $derived(folderId === null ? [] : pathTo(outline, folderId));
	const cards = $derived(folderId === null ? outline : (findItem(outline, folderId)?.children ?? []));

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
		// A folder that no longer exists (deleted elsewhere) falls back to the top level.
		if (folderId !== null && !findItem(outline, folderId)) folderId = null;
	}

	onMount(async () => {
		if (!PROJECT) {
			loading = false;
			return;
		}
		try {
			await load();
		} catch (e) {
			error = msg(e, 'Failed to load cards');
		} finally {
			loading = false;
		}
	});

	function open(card: OutlineItem) {
		if (card.type === 'folder') folderId = card.id;
		else goto(`/write?scene=${card.id}`);
	}

	/** Move a card one place earlier (-1) or later (+1) among its siblings. */
	async function shift(card: OutlineItem, by: -1 | 1) {
		const to = card.position + by;
		if (busy || to < 0 || to >= cards.length) return;
		busy = true;
		try {
			await call('POST /api/projects/{name}/outline/{item_id}/move', {
				params: { name: PROJECT, item_id: card.id },
				body: { parent_id: folderId, position: to }
			});
			await load();
		} catch (e) {
			error = msg(e, 'Could not move the card');
		} finally {
			busy = false;
		}
	}

	/** Move a card out of this folder, to sit just after it in the folder above. */
	async function moveUp(card: OutlineItem) {
		if (busy || folderId === null) return;
		const here = trail[trail.length - 1];
		busy = true;
		try {
			await call('POST /api/projects/{name}/outline/{item_id}/move', {
				params: { name: PROJECT, item_id: card.id },
				body: { parent_id: here.parent_id, position: here.position + 1 }
			});
			await load();
		} catch (e) {
			error = msg(e, 'Could not move the card');
		} finally {
			busy = false;
		}
	}

	/**
	 * Touch drag-and-drop: hold a card for 350ms to lift it, drag it anywhere
	 * on the grid, drop it. On touch the grid has `touch-action: none`
	 * (layout.css), so a hold always wins over page scrolling; while dragging,
	 * SortableJS auto-scrolls the page when the card nears an edge.
	 */
	$effect(() => {
		const el = gridEl;
		if (!el || view !== 'grid' || loading) return;
		const sortable = Sortable.create(el, {
			draggable: 'li[data-card]',
			animation: 150,
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
			onEnd: onDropEnd
		});
		return () => sortable.destroy();
	});

	/** The drop landed: update the tree optimistically, then persist it. */
	function onDropEnd(evt: Sortable.SortableEvent) {
		const from = evt.oldDraggableIndex;
		const to = evt.newDraggableIndex;
		const id = Number(evt.item?.dataset.card);
		if (from === undefined || to === undefined || from === to || !Number.isFinite(id)) return;
		const position = sameParentPosition(from, to);
		let next: OutlineItem[];
		try {
			// The grid holds one folder's children, so the move is always within
			// the same parent; `position` is the after-detach index for it.
			next = moveItem(outline, id, folderId, position);
		} catch {
			void load(); // DOM and state disagree; resynchronise from the server
			return;
		}
		outline = next; // Svelte re-renders in the order SortableJS already applied
		call('POST /api/projects/{name}/outline/{item_id}/move', {
			params: { name: PROJECT, item_id: id },
			body: { parent_id: folderId, position }
		}).catch(async (e) => {
			error = msg(e, 'Could not move the card');
			await load();
		});
	}

	async function addCard(e: SubmitEvent) {
		e.preventDefault();
		const title = newTitle.trim();
		if (!title || busy) return;
		busy = true;
		try {
			await call('POST /api/projects/{name}/outline', {
				params: { name: PROJECT },
				body: { title, type: 'md', parent_id: folderId }
			});
			newTitle = '';
			adding = false;
			await load();
		} catch (e) {
			error = msg(e, 'Could not add the card');
		} finally {
			busy = false;
		}
	}
</script>

<AppShell title="Cards">
<div class="mx-auto flex max-w-4xl flex-col gap-4">
{#if !PROJECT}
<NoProject />
{:else if loading}
<p class="py-12 text-center" style="color: var(--muted)">Loading cards...</p>
{:else}
{#if error}
<p role="alert" class="flex items-start gap-2" style="color: var(--danger)">
<span class="flex-1">{error}</span>
<button class="text-xs underline" type="button" onclick={() => (error = '')}>Dismiss</button>
</p>
{/if}

<nav aria-label="Folder" class="flex flex-wrap items-center gap-1 text-sm">
<button type="button" class="rounded px-2 py-1" style="color: {folderId === null ? 'inherit' : 'var(--accent)'}" onclick={() => (folderId = null)}>All</button>
{#each trail as f (f.id)}
<ChevronRight size={14} style="color: var(--muted)" />
<button type="button" class="rounded px-2 py-1" style="color: {f.id === folderId ? 'inherit' : 'var(--accent)'}" onclick={() => (folderId = f.id)}>{f.title}</button>
{/each}
</nav>

<!-- View toggle -->
<div class="flex items-center gap-1 text-sm">
<button type="button" class="flex items-center gap-1 rounded px-2 py-1" style="background: {view === 'grid' ? 'var(--accent)' : 'transparent'}; color: {view === 'grid' ? 'var(--accent-text)' : 'var(--muted)'}" onclick={() => (view = 'grid')}><LayoutGrid size={14} /> Grid</button>
<button type="button" class="flex items-center gap-1 rounded px-2 py-1" style="background: {view === 'flow' ? 'var(--accent)' : 'transparent'}; color: {view === 'flow' ? 'var(--accent-text)' : 'var(--muted)'}" onclick={() => (view = 'flow')}><Waypoints size={14} /> Flow</button>
</div>

{#if view === 'grid'}
<ul class="cork-grid grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label="Cards" bind:this={gridEl}>
{#each cards as card, i (card.id)}
{@const color = labelColor(labels, card.label)}
{@const status = card.status ? (statusList[Number(card.status) - 1] ?? '') : ''}
<li data-card={card.id} class="flex flex-col overflow-hidden rounded-lg border" style="background: var(--surface); border-color: var(--border)">
<div class="h-1.5" style="background: {color || 'transparent'}"></div>
<button type="button" class="flex flex-1 flex-col gap-2 p-3 text-left" aria-label="Open {card.title}" onclick={() => open(card)}>
<span class="flex items-center gap-2 font-medium">
{#if card.type === 'folder'}<Folder size={16} style="color: var(--muted)" />{:else}<FileText size={16} style="color: var(--muted)" />{/if}
<span class="min-w-0 flex-1 truncate">{card.title}</span>
</span>
<span class="line-clamp-4 text-sm" style="color: var(--muted)">{card.summary_sentence || card.summary_full || 'No summary yet'}</span>
<span class="mt-auto flex items-center gap-2 text-xs" style="color: var(--muted)">
<span>{card.words.toLocaleString()} words</span>
{#if status}<span class="rounded border px-1.5" style="border-color: var(--border)">{status}</span>{/if}
</span>
</button>
<div class="flex items-center justify-end gap-1 border-t px-1" style="border-color: var(--border)">
<button type="button" class="tap flex size-9 items-center justify-center rounded disabled:opacity-30" aria-label="Move {card.title} earlier" disabled={busy || dragging || i === 0} onclick={() => shift(card, -1)}><ChevronLeft size={16} /></button>
<button type="button" class="tap flex size-9 items-center justify-center rounded disabled:opacity-30" aria-label="Move {card.title} later" disabled={busy || dragging || i === cards.length - 1} onclick={() => shift(card, 1)}><ChevronRight size={16} /></button>
{#if folderId !== null}
<button type="button" class="tap flex size-9 items-center justify-center rounded disabled:opacity-30" aria-label="Move {card.title} out of this folder" disabled={busy || dragging} onclick={() => moveUp(card)}><ChevronUp size={16} /></button>
{/if}
</div>
</li>
{/each}

<li>
{#if adding}
<form onsubmit={addCard} class="flex flex-col gap-2 rounded-lg border p-3" style="border-color: var(--accent)">
<input class="rounded border px-2 py-1 text-sm" style="background: var(--surface); border-color: var(--border)" aria-label="New scene title" placeholder="Scene title" bind:value={newTitle} required />
<div class="flex gap-2">
<button class="flex-1 rounded px-3 py-1.5 text-sm font-medium disabled:opacity-60" style="background: var(--accent); color: var(--accent-text)" disabled={busy}>Add</button>
<button type="button" class="rounded border px-3 py-1.5 text-sm" style="border-color: var(--border)" onclick={() => { adding = false; newTitle = ''; }}>Cancel</button>
</div>
</form>
{:else}
<button type="button" class="flex min-h-24 w-full items-center justify-center gap-2 rounded-lg border border-dashed text-sm" style="border-color: var(--border); color: var(--muted)" onclick={() => (adding = true)}><Plus size={16} /> Add scene</button>
{/if}
</li>
</ul>
{:else}
<Whiteboard project={PROJECT} items={outline} {labels} {statusList} />
{/if}
{/if}
</div>
</AppShell>
