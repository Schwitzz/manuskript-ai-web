<script lang="ts">
	import { SvelteFlow, Controls, MiniMap, Background, addEdge, type Node, type Edge, type Connection } from '@xyflow/svelte';
	import WhiteboardCard from './WhiteboardCard.svelte';
	import { call, ApiError } from '#lib/api';
	import { goto } from '$app/navigation';
	import type { LabelDef, OutlineItem } from '#lib/outline';
	import { mergeLayout, type SavedLayout, buildNodes, filterEdges, collectIds } from '#lib/whiteboard';
	import { Plus, Folder, Trash2, Undo2, ZoomIn, ZoomOut, Move, X } from '@lucide/svelte';

	let {
		project,
		items,
		labels,
		statusList
	}: {
		project: string;
		items: OutlineItem[];
		labels: LabelDef[];
		statusList: string[];
	} = $props();

	let nodes = $state.raw<any[]>([]);
	let edges = $state.raw<Edge[]>([]);
	let viewport = $state<{ x: number; y: number; zoom: number } | undefined>(undefined);
	let saving = $state(false);
	let adding = $state(false);
	let newTitle = $state('');
	let newType = $state<'scene' | 'folder'>('scene');
	let selectedNodeId = $state<number | null>(null);
	let selectedEdgeId = $state<string | null>(null);
	let error = $state('');
	let busy = $state(false);

	const nodeTypes = { card: WhiteboardCard } as any;
	let flowEl: HTMLDivElement | undefined;

	// Initial load: fetch saved layout, merge with current items
	$effect(() => {
		if (!project || items.length === 0) return;
		let cancelled = false;
		(async () => {
			try {
				const layout = await call('GET /api/projects/{name}/whiteboard', { params: { name: project } });
				if (cancelled) return;
				const { nodes: mergedNodes, edges: mergedEdges, viewport: mergedViewport } =
					mergeLayout(items, labels, statusList, layout as SavedLayout);
				nodes = mergedNodes.map((n: any) => ({ ...n, type: 'card' }));
				edges = mergedEdges;
				viewport = mergedViewport;
			} catch (e) {
				if (cancelled) return;
				const { nodes: defaultNodes, edges: defaultEdges, viewport: defaultViewport } =
					mergeLayout(items, labels, statusList, null);
				nodes = defaultNodes.map((n: any) => ({ ...n, type: 'card' }));
				edges = defaultEdges;
				viewport = defaultViewport;
			}
		})();
		return () => { cancelled = true; };
	});

	// Save when nodes or edges change
	let saveTimer: ReturnType<typeof setTimeout> | null = null;
	function scheduleSave() {
		if (saveTimer) clearTimeout(saveTimer);
		saveTimer = setTimeout(save, 800);
	}

	async function save() {
		if (!project || saving) return;
		saving = true;
		try {
			await call('PUT /api/projects/{name}/whiteboard', {
				params: { name: project },
				body: {
					version: 1,
					nodes: nodes.map((n: any) => ({
						id: n.id,
						position: { x: n.position?.x ?? 0, y: n.position?.y ?? 0 }
					})),
					edges: edges.map(e => ({
						id: e.id,
						source: e.source,
						target: e.target
					})),
					viewport
				}
			});
		} catch { /* silent – will retry on next change */ }
		finally { saving = false; }
	}

	$effect(() => { nodes; edges; if (nodes.length > 0) scheduleSave(); });

	// Connect handler
	function handleConnect(conn: Connection) {
		edges = addEdge(conn, edges);
	}

	// Node selection
	function handleNodeSelect(id: number | null) {
		selectedNodeId = id;
		selectedEdgeId = null;
	}

	// Node removal
	async function removeNode(id: number) {
		const node = nodes.find((n: any) => Number(n.id) === id);
		if (!node) return;
		const title = (node.data as any).title;
		if (!confirm(`Remove "${title}" from the whiteboard? (It stays in the outline.)`)) return;
		const item = items.find(i => i.id === id);
		const parent = item?.parent_id;
		const pos = item?.position ?? 0;
		nodes = nodes.filter((n: any) => Number(n.id) !== id);
		edges = edges.filter(e => e.source !== String(id) && e.target !== String(id));
		selectedNodeId = null;
		if (parent !== null) {
			await call('POST /api/projects/{name}/outline/{item_id}/move', {
				params: { name: project, item_id: id },
				body: { parent_id: null, position: pos }
			}).catch(e => error = msg(e, 'Could not unplace'));
		} else {
			await call('DELETE /api/projects/{name}/outline/{item_id}', {
				params: { name: project, item_id: id }
			}).catch(e => error = msg(e, 'Could not delete'));
		}
		await loadOutline();
		scheduleSave();
	}

	// Node rename
	async function renameNode(id: number, title: string) {
		const clean = title.trim();
		const node = items.find(i => i.id === id);
		if (!clean || !node || clean === node.title) return;
		node.title = clean;
		try {
			await call('PATCH /api/projects/{name}/outline/{item_id}/title', {
				params: { name: project, item_id: id },
				body: { title: clean }
			});
		} catch (e) {
			node.title = ''; // restore
			error = msg(e, 'Could not rename');
		}
	}

	// Open node in editor
	function openInEditor(id: number) {
		goto(`/write?scene=${id}`);
	}

	// Add a new scene/folder on the whiteboard (positioned near the selected node or center)
	async function addNode() {
		const title = newTitle.trim();
		if (!title || busy) return;
		busy = true;
		try {
			const node = await call('POST /api/projects/{name}/outline', {
				params: { name: project },
				body: { title, type: newType === 'scene' ? 'md' : 'folder', parent_id: null }
			});
			// Place the new node at center of viewport
			const vp = viewport ?? { x: 0, y: 0, zoom: 1 };
			const cx = vp.x + 800 / (vp.zoom ?? 1) / 2 - 144;
			const cy = vp.y + 300 / (vp.zoom ?? 1) / 2 - 100;
			nodes = [...nodes, {
				id: String(node.id),
				position: { x: cx, y: cy },
				type: 'card',
				data: {
					id: node.id,
					title: node.title,
					type: node.type,
					summary: '',
					words: 0,
					label: '',
					color: '',
					status: ''
				}
			}];
			newTitle = '';
			adding = false;
			await loadOutline();
			scheduleSave();
		} catch (e) {
			error = msg(e, 'Could not add');
		} finally {
			busy = false;
		}
	}

	// Delete selected edge
	function deleteEdge() {
		if (selectedEdgeId) {
			edges = edges.filter(e => e.id !== selectedEdgeId);
			selectedEdgeId = null;
		}
	}

	// Keyboard shortcuts
	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Delete' || e.key === 'Backspace') {
			if (selectedNodeId) {
				e.preventDefault();
				removeNode(selectedNodeId);
			} else if (selectedEdgeId) {
				e.preventDefault();
				deleteEdge();
			}
		}
		if (e.key === 'Escape') {
			selectedNodeId = null;
			selectedEdgeId = null;
			if (adding) { adding = false; newTitle = ''; }
		}
	}

	// Zoom controls
	function zoomIn() {
		if (!viewport) return;
		viewport = { ...viewport, zoom: Math.min(viewport.zoom * 1.2, 3) };
		scheduleSave();
	}
	function zoomOut() {
		if (!viewport) return;
		viewport = { ...viewport, zoom: Math.max(viewport.zoom / 1.2, 0.1) };
		scheduleSave();
	}
	function resetView() {
		viewport = { x: 0, y: 0, zoom: 1 };
		scheduleSave();
	}

	function msg(e: unknown, fallback: string): string {
		return e instanceof ApiError || e instanceof Error ? e.message : fallback;
	}

	async function loadOutline() {
		try {
			const o = await call('GET /api/projects/{name}/outline', { params: { name: project } });
			const { nodes: newNodes } = mergeLayout(o.items as unknown as OutlineItem[], labels, statusList, null);
			// Keep existing nodes' positions
			const savedPos: Record<string, { x: number; y: number }> = {};
			for (const n of nodes) savedPos[n.id] = { ...(n.position ?? { x: 0, y: 0 }) };
			// Merge: keep existing nodes' positions, add new nodes
			const oldIds = new Set(nodes.map((n: any) => n.id));
			nodes = newNodes.map((n: any) => {
				if (oldIds.has(n.id)) {
					return { ...n, position: savedPos[n.id] ?? n.position };
				}
				return n;
			});
		} catch { /* ignore */ }
	}
</script>

<div class="relative h-full w-full overflow-hidden rounded-lg" style="background: var(--bg)">
	<!-- Error toast -->
	{#if error}
		<div class="absolute right-4 top-4 z-50 rounded-lg border p-3 text-sm"
			style="background:var(--surface); border-color:var(--danger); color:var(--danger)"
			onclick={() => (error = '')}>
			{error} · click to dismiss
		</div>
	{/if}

	<!-- Toolbar -->
	<div class="absolute left-4 top-4 z-40 flex items-center gap-1">
		{#if adding}
			<!-- Add form -->
			<form onsubmit={(e) => { e.preventDefault(); addNode(); }} class="flex items-center gap-1 rounded-lg border p-1"
				style="background:var(--surface); border-color:var(--border)">
				<select class="rounded border px-2 py-1 text-xs" style="background:var(--surface); border-color:var(--border)"
					bind:value={newType}>
					<option value="scene">Scene</option>
					<option value="folder">Folder</option>
				</select>
				<input class="w-36 rounded border px-2 py-1 text-sm" style="background:var(--surface); border-color:var(--border)"
					aria-label="New item title" placeholder="Title" bind:value={newTitle} required />
				<button class="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium"
					style="background:var(--accent); color:var(--accent-text)" disabled={busy} type="submit">Add</button>
				<button class="tap rounded p-1" type="button" onclick={() => { adding = false; newTitle = ''; }}>
					<Undo2 size={14} style="color:var(--muted)" />
				</button>
			</form>
		{:else}
			<button class="tap flex items-center gap-1 rounded-lg border px-3 py-2 text-sm"
				style="background:var(--surface); border-color:var(--border)" type="button"
				onclick={() => (adding = true)}>
				<Plus size={16} /> Add
			</button>
			<button class="tap rounded p-2" style="background:var(--surface); border-color:var(--border)"
				title="Fit view" type="button"
				onclick={() => {
					nodes = nodes.map((n: any) => ({ ...n, type: 'card' }));
					edges = edges.map((e: any) => ({ ...e, type: 'default' }));
				}}>
				<Move size={16} style="color:var(--muted)" />
			</button>
		{/if}
	</div>

	<!-- Zoom / reset controls (bottom-right) -->
	<div class="absolute right-4 bottom-4 z-40 flex items-center gap-1">
		<button class="tap rounded-lg border p-2" style="background:var(--surface); border-color:var(--border)"
			title="Zoom in" type="button" onclick={zoomIn}><ZoomIn size={16} /></button>
		<button class="tap rounded-lg border p-2" style="background:var(--surface); border-color:var(--border)"
			title="Zoom out" type="button" onclick={zoomOut}><ZoomOut size={16} /></button>
		<button class="tap rounded-lg border p-2" style="background:var(--surface); border-color:var(--border)"
			title="Reset view" type="button" onclick={resetView}><Undo2 size={16} /></button>
	</div>

	<!-- Edge deletion confirmation (centered) -->
	{#if selectedEdgeId}
		<div class="absolute left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 rounded-lg border p-3 text-center"
			style="background:var(--surface); border-color:var(--border)">
			<p class="mb-2 text-sm">Edge selected.</p>
			<div class="flex gap-2 justify-center">
				<button class="rounded-lg border px-3 py-1 text-sm" type="button"
					onclick={() => deleteEdge()}>Delete</button>
				<button class="rounded-lg border px-3 py-1 text-sm" type="button"
					onclick={() => selectedEdgeId = null}>Cancel</button>
			</div>
		</div>
	{/if}

	<!-- Flow canvas (wrapper div for bind:this) -->
	<div bind:this={flowEl}>
		<SvelteFlow
			bind:nodes
			bind:edges
			bind:viewport
			{nodeTypes}
			onconnect={handleConnect}
			onnodeclick={(e) => {
				const node = e.node;
				if (selectedNodeId === Number(node.id)) handleNodeSelect(null);
				else handleNodeSelect(Number(node.id));
				selectedEdgeId = null;
			}}
			onedgeclick={(e) => {
				selectedEdgeId = e.edge.id;
				selectedNodeId = null;
			}}
			fitView
			panOnScroll
			panOnDrag
		>
			<Background />
			<Controls />
			<MiniMap />
		</SvelteFlow>
	</div>

	<!-- Selection info bar (bottom-left) -->
	{#if selectedNodeId}
		<div class="absolute left-4 bottom-4 z-40 flex items-center gap-2 rounded-lg border px-3 py-2"
			style="background:var(--accent)/90; color:var(--accent-text)">
			<span class="text-sm font-medium">{(nodes.find((n: any) => Number(n.id) === selectedNodeId)?.data as any)?.title ?? 'Selected'}</span>
			<span class="text-xs opacity-70">Press Delete to remove</span>
			<button class="rounded p-1" onclick={() => handleNodeSelect(null)} type="button">
				<X size={14} />
			</button>
		</div>
	{:else if selectedEdgeId}
		<div class="absolute left-4 bottom-4 z-40 flex items-center gap-2 rounded-lg border px-3 py-2"
			style="background:var(--accent)/90; color:var(--accent-text)">
			<span class="text-sm font-medium">Edge selected</span>
			<span class="text-xs opacity-70">Press Delete to remove</span>
			<button class="rounded p-1" onclick={() => selectedEdgeId = null} type="button">
				<X size={14} />
			</button>
		</div>
	{/if}
</div>

<!-- Keyboard listener -->
<svelte:window onkeydown={onKeydown} />
