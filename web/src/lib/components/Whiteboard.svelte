<script lang="ts">
	import { SvelteFlow, Controls, MiniMap, Background, addEdge, type Node, type Edge, type Connection } from '@xyflow/svelte';
	import WhiteboardCard from './WhiteboardCard.svelte';
	import { call } from '#lib/api';
	import type { LabelDef, OutlineItem } from '#lib/outline';
	import { mergeLayout, type SavedLayout } from '#lib/whiteboard';

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

	let nodes = $state.raw<Node[]>([]);
	let edges = $state.raw<Edge[]>([]);
	let viewport = $state<{ x: number; y: number; zoom: number } | undefined>(undefined);
	let saving = $state(false);

	const nodeTypes = { card: WhiteboardCard };

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
				nodes = mergedNodes.map(n => ({ ...n, type: 'card' })) as Node[];
				edges = mergedEdges;
				viewport = mergedViewport;
			} catch {
				// No saved layout – place nodes in default positions
				if (cancelled) return;
				const { nodes: defaultNodes, edges: defaultEdges, viewport: defaultViewport } =
					mergeLayout(items, labels, statusList, null);
				nodes = defaultNodes.map(n => ({ ...n, type: 'card' })) as Node[];
				edges = defaultEdges;
				viewport = defaultViewport;
			}
		})();
		return () => { cancelled = true; };
	});

	function handleConnect(conn: Connection) {
		edges = addEdge(conn, edges);
	}

	/** Debounced save of the current layout to the server. */
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
					nodes: nodes.map(n => ({
						id: n.id,
						position: { x: n.position.x, y: n.position.y }
					})),
					edges: edges.map(e => ({
						id: e.id,
						source: e.source,
						target: e.target
					})),
					viewport
				}
			});
		} catch {
			// silent – will retry on next change
		} finally {
			saving = false;
		}
	}

	// Save when nodes or edges change
	$effect(() => {
		nodes; edges; // track
		if (nodes.length > 0) scheduleSave();
	});
</script>

<div class="h-full w-full overflow-hidden rounded-lg" style="background: var(--bg)">
	<SvelteFlow
		bind:nodes
		bind:edges
		bind:viewport
		{nodeTypes}
		onconnect={handleConnect}
		fitView
		panOnScroll
		panOnDrag
	>
		<Background />
		<Controls />
		<MiniMap />
	</SvelteFlow>
</div>