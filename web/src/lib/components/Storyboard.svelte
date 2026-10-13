<script lang="ts">
	import { onMount } from 'svelte';
	import StoryboardCard from './StoryboardCard.svelte';
	import { findItem, type OutlineItem, type LabelDef, flatten } from '#lib/outline.ts';
	import { call, ApiError } from '#lib/api';
	import { goto } from '$app/navigation';
	import { sameParentPosition } from '#lib/dnd.ts';
	import {
		Plus, Trash2, FolderOpen, X, FileText, Pencil,
		Check, ChevronDown, ChevronUp,
	} from '@lucide/svelte';
	import { addToast } from '#lib/stores/toast.svelte.ts';

	let {
		project,
		items,
		labels,
		statusList,
	}: {
		project: string;
		items: OutlineItem[];
		labels: LabelDef[];
		statusList: string[];
	} = $props();

	let flow = $derived(sceneFlow(items));
	let cols = $derived(getCols());
	let rows = $derived(computeRows());
	let selectedIndex = $state(-1);

	/** Get the flow index at a given row/col position (serpentine-aware). */
	function cardAt(row: { start: number; end: number; dir: 1 | -1 }, colIdx: number): number {
		return row.dir === 1 ? row.start + colIdx : row.end - 1 - colIdx;
	}
	let adding = $state(false);
	let newTitle = $state('');
	let newType = $state<'scene' | 'folder'>('scene');
	let renamingId = $state<number | null>(null);
	let renameTitle = $state('');
	let deleteId = $state<number | null>(null);
	let error = $state('');

	function getCols(): number {
		const w = typeof window !== 'undefined' ? window.innerWidth : 1440;
		return w < 640 ? 2 : w < 1024 ? 3 : 4;
	}

	function computeRows(): { start: number; end: number; dir: 1 | -1 }[] {
		const result: { start: number; end: number; dir: 1 | -1 }[] = [];
		const maxIdx = flow.length;
		let i = 0;
		while (i < maxIdx) {
			const end = Math.min(i + cols, flow.length);
			if (end > i) {
				const dir = (Math.floor(i / cols) % 2 === 0) ? 1 : -1;
				result.push({ start: i, end, dir });
			}
			i = end;
		}
		return result;
	}

	function sceneFlow(items: OutlineItem[]): OutlineItem[] {
		return flatten(items).filter((i) => i.type !== 'folder');
	}

	async function moveEarlier(id: number): Promise<void> {
		const item = findItem(items, id);
		if (!item || item.type === 'folder') return;
		const parent = item.parent_id != null ? findItem(items, item.parent_id) : null;
		if (!parent || parent.type !== 'folder') return;
		const siblings = parent.children;
		const idx = siblings.findIndex((s) => s.id === id);
		if (idx <= 0) { addToast('Already first'); return; }
		const newPos = sameParentPosition(idx, idx - 1);
		try {
			await call('POST /api/projects/{name}/outline/{item_id}/move', {
				params: { name: project, item_id: id },
				body: { parent_id: item.parent_id, position: newPos },
			});
			addToast('Moved earlier');
		} catch (e: unknown) {
			error = e instanceof ApiError ? e.message : 'Move failed';
		}
	}

	async function moveLater(id: number): Promise<void> {
		const item = findItem(items, id);
		if (!item || item.type === 'folder') return;
		const parent = item.parent_id != null ? findItem(items, item.parent_id) : null;
		if (!parent || parent.type !== 'folder') return;
		const siblings = parent.children;
		const idx = siblings.findIndex((s) => s.id === id);
		if (idx >= siblings.length - 1) { addToast('Already last'); return; }
		const newPos = sameParentPosition(idx, idx + 1);
		try {
			await call('POST /api/projects/{name}/outline/{item_id}/move', {
				params: { name: project, item_id: id },
				body: { parent_id: item.parent_id, position: newPos },
			});
			addToast('Moved later');
		} catch (e: unknown) {
			error = e instanceof ApiError ? e.message : 'Move failed';
		}
	}

	async function moveOutOfFolder(id: number): Promise<void> {
		const item = findItem(items, id);
		if (!item || !item.parent_id) return;
		const parent = findItem(items, item.parent_id);
		if (!parent || parent.type !== 'folder') return;
		try {
			await call('POST /api/projects/{name}/outline/{item_id}/move', {
				params: { name: project, item_id: id },
				body: { parent_id: null, position: items.findIndex((t) => t.id === item.parent_id) + 1 },
			});
			addToast('Moved out of folder');
		} catch (e: unknown) {
			error = e instanceof ApiError ? e.message : 'Move failed';
		}
	}

	async function confirmDelete(): Promise<void> {
		if (!deleteId) return;
		try {
			await call('DELETE /api/projects/{name}/outline/{item_id}', {
				params: { name: project, item_id: deleteId },
			});
			deleteId = null;
			selectedIndex = -1;
			addToast('Deleted');
		} catch (e: unknown) {
			error = e instanceof ApiError ? e.message : 'Delete failed';
		}
	}

	async function handleAdd(): Promise<void> {
		if (!newTitle.trim()) return;
		try {
			await call('POST /api/projects/{name}/outline', {
				params: { name: project },
				body: {
					title: newTitle.trim(),
					type: newType === 'scene' ? 'md' : 'folder',
					parent_id: null,
					position: items.length,
				},
			});
			adding = false;
			newTitle = '';
			addToast('Added');
		} catch (e: unknown) {
			error = e instanceof ApiError ? e.message : 'Add failed';
		}
	}

	async function saveRename(): Promise<void> {
		if (!renamingId) return;
		try {
			await call('PATCH /api/projects/{name}/outline/{item_id}/title', {
				params: { name: project, item_id: renamingId },
				body: { title: renameTitle.trim() || 'Untitled' },
			});
			renamingId = null;
			renameTitle = '';
			addToast('Renamed');
		} catch (e: unknown) {
			error = e instanceof ApiError ? e.message : 'Rename failed';
		}
	}

	function openScene(id: number): void {
		goto(`/write?scene=${id}`);
	}

	function canMoveEarlier(item: OutlineItem): boolean {
		if (item.type === 'folder') return true;
		const parent = item.parent_id != null ? findItem(items, item.parent_id) : null;
		if (!parent || parent.type !== 'folder') return true;
		return parent.children.findIndex((s) => s.id === item.id) <= 0;
	}

	function canMoveLater(item: OutlineItem): boolean {
		if (item.type === 'folder') return true;
		const parent = item.parent_id != null ? findItem(items, item.parent_id) : null;
		if (!parent || parent.type !== 'folder') return true;
		return parent.children.findIndex((s) => s.id === item.id) >= parent.children.length - 1;
	}

	onMount(() => {
		window.addEventListener('resize', () => void (cols = getCols()));
	});
</script>

<!-- Add scene form -->
{#if adding}
	<div class="flex gap-2 rounded-lg border p-3" style="background:var(--surface)">
		<select
			aria-label="New item type"
			class="rounded border px-2 py-1 text-sm"
			style="border-color:var(--border)"
			value={newType}
			onchange={(e) => (newType = (e.target as HTMLSelectElement).value as 'scene' | 'folder')}
		>
			<option value="scene">Scene</option>
			<option value="folder">Folder</option>
		</select>
		<input
			aria-label="New item title"
			class="flex-1 rounded border px-2 py-1 text-sm"
			style="border-color:var(--border)"
			value={newTitle}
			oninput={(e) => (newTitle = (e.target as HTMLInputElement).value)}
			onkeydown={(e) => { if (e.key === 'Enter') handleAdd(); }}
		/>
		<button
			class="rounded px-3 py-1 text-sm font-medium"
			style="background:var(--primary); color:var(--primary-foreground)"
			onclick={handleAdd}
		>
			Add
		</button>
		<button class="rounded px-2 py-1 text-sm" style="background:transparent" onclick={() => (adding = false)}>
			<X size={16} />
		</button>
	</div>
{/if}

<!-- Error -->
{#if error}
	<div class="mb-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
		onclick={() => (error = '')} role="alert">
		{error}
	</div>
{/if}

<!-- Action bar -->
{#if selectedIndex >= 0}
	<div class="sticky bottom-0 z-10 flex items-center gap-2 overflow-x-auto rounded-t-lg border-t bg-card px-3 py-2 shadow-lg">
		{#if renamingId === flow[selectedIndex]?.id}
			<input
				aria-label="Rename scene"
				class="min-w-[140px] flex-1 rounded border px-2 py-1 text-sm"
				style="border-color:var(--border)"
				value={renameTitle}
				oninput={(e) => (renameTitle = (e.target as HTMLInputElement).value)}
				onkeydown={(e) => { if (e.key === 'Enter') saveRename(); }}
			/>
			<button class="shrink-0 rounded p-1" onclick={saveRename} title="Save rename">
				<Check size={16} />
			</button>
			<button class="shrink-0 rounded p-1" onclick={() => (renamingId = null)} title="Cancel">
				<X size={16} />
			</button>
		{:else}
			<button class="shrink-0 rounded px-2 py-1 text-xs font-medium"
				style="background:var(--primary); color:var(--primary-foreground)"
				onclick={() => openScene(flow[selectedIndex].id)} title="Open in editor">
				<FileText size={14} />
			</button>
			<button class="shrink-0 rounded p-1" style="background:transparent"
				onclick={() => { renamingId = flow[selectedIndex].id; renameTitle = flow[selectedIndex].title; }}
				title="Rename"><Pencil size={16} /></button>
			<button class="shrink-0 rounded p-1" style="background:transparent"
				onclick={() => moveEarlier(flow[selectedIndex].id)} title="Move earlier"
				disabled={canMoveEarlier(flow[selectedIndex])}>
				<ChevronUp size={16} />
			</button>
			<button class="shrink-0 rounded p-1" style="background:transparent"
				onclick={() => moveLater(flow[selectedIndex].id)} title="Move later"
				disabled={canMoveLater(flow[selectedIndex])}>
				<ChevronDown size={16} />
			</button>
			{#if flow[selectedIndex].parent_id}
				<button class="shrink-0 rounded p-1" style="background:transparent"
					onclick={() => moveOutOfFolder(flow[selectedIndex].id)} title="Move out of folder">
					<FolderOpen size={16} />
				</button>
			{/if}
			{#if deleteId === flow[selectedIndex].id}
				<span class="text-xs text-destructive">Delete? </span>
				<button class="rounded bg-destructive px-2 py-1 text-xs font-medium text-destructive-foreground"
					onclick={confirmDelete}>Yes</button>
				<button class="rounded px-2 py-1 text-xs" style="background:transparent"
					onclick={() => (deleteId = null)}>Cancel</button>
			{:else}
				<button class="shrink-0 rounded p-1 text-destructive" style="background:transparent"
					onclick={() => (deleteId = flow[selectedIndex].id)} title="Delete">
					<Trash2 size={16} />
				</button>
			{/if}
			<button class="shrink-0 rounded p-1" style="background:transparent"
				onclick={() => (selectedIndex = -1)} title="Deselect">
				<X size={16} />
			</button>
		{/if}
	</div>
{/if}

<!-- Serpentine grid -->
<div class="relative pb-24">
	{#each rows as row, rowIndex}
		<div class="grid gap-2 px-2 py-1" class:grid-cols-2={cols === 2} class:grid-cols-3={cols === 3} class:grid-cols-4={cols === 4}>
			{#each Array(cols).fill(0) as _, colIdx}
				{#if cardAt(row, colIdx) < flow.length}
					<StoryboardCard
						item={flow[cardAt(row, colIdx)]}
						{labels}
						{statusList}
						selected={cardAt(row, colIdx) === selectedIndex}
						onSelect={() => (selectedIndex = cardAt(row, colIdx))}
						onOpen={() => openScene(flow[cardAt(row, colIdx)].id)}
					/>
				{/if}
			{/each}
		</div>
		{#if rowIndex < rows.length - 1}
			<div class="flex items-center justify-center py-2">
				<span class="text-muted-foreground" style="font-size:20px">▼</span>
			</div>
		{/if}
	{/each}
</div>
