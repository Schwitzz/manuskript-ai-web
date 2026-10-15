<script lang="ts">
	import '@xyflow/svelte/dist/style.css';
	import AppShell from '#lib/components/AppShell.svelte';
	import { project } from '#lib/stores/project.svelte.ts';
	import { onMount, onDestroy } from 'svelte';
	import {
		SvelteFlow,
		Background,
		ConnectionMode,
		type Connection,
		type Node,
		type Edge,
		type NodeTypes,
		type Viewport
	} from '@xyflow/svelte';
	import {
		Square, Circle, Triangle, ArrowRight,
		Type, Trash2, Plus,
		Minimize, ZoomIn, ZoomOut, StickyNote
	} from '@lucide/svelte';
	import { LINE_TYPES } from '#lib/whiteboard/line-types';
	import ShapeNode from './ShapeNode.svelte';
	import NoteNode from './NoteNode.svelte';
	import DashedEdge from './DashedEdge.svelte';

	const PROJECT = project.name || 'whiteboard';
	const STORAGE_KEY = `msk_whiteboard_${PROJECT}`;

	const nodeTypes: NodeTypes = {
		shape: ShapeNode as unknown as NodeTypes['shape'],
		note: NoteNode as unknown as NodeTypes['note']
	};

	const edgeTypes = {
		dashed: DashedEdge
	};

	let canvasEl: HTMLDivElement | undefined = $state();
	let nodes = $state<Node[]>([]);
	let edges = $state<Edge[]>([]);
	let selectedId = $state<string | null>(null);
	let selectedEdgeId = $state<string | null>(null);
	let toolbarOpen = $state(false);
	let toolbarMenuOpen = $state(false);
	let connectionMode = $state(false);
	let connectFromId = $state<string | null>(null);
	let pointerDownNodeId = $state<string | null>(null);
	let selectedNodeShape = $state('rectangle');
	let edgeLineType = $state<'solid' | 'dash' | 'dot' | 'solid-dashed'>('solid');
	let showAllNotes = $state(false);
	let lineTypeMenuOpen = $state(false);

	function selectLineType(lineType: 'solid' | 'dash' | 'dot' | 'solid-dashed') {
		edgeLineType = lineType;
		lineTypeMenuOpen = false;
		if (selectedEdgeId) {
			edges = edges.map((e) =>
				e.id === selectedEdgeId
					? { ...e, type: 'dashed', data: { ...e.data, lineType } }
					: e
			);
			save();
		}
		connectionMode = true;
		connectFromId = null;
	}

	let error = $state('');
	let viewport = $state<Viewport>({ x: 0, y: 0, zoom: 1 });
	let autoSaveTimer: ReturnType<typeof setTimeout> | null = null;

	const selectedNode = $derived(selectedId ? (nodes.find((n) => n.id === selectedId) ?? null) : null);

	function patchNodeData(nodeId: string, patch: { label?: string; note?: string }) {
		nodes = nodes.map((n) =>
			n.id === nodeId
				? { ...n, data: { ...n.data, ...patch } }
				: n
		);
		save();
	}

	function attachNodeCallbacks(rawNodes: Node[]): Node[] {
		return rawNodes.map((n) => ({
			...n,
			data: {
				...n.data,
				showNotes: showAllNotes,
				onUpdate: (patch: { label?: string; note?: string }) => patchNodeData(n.id, patch)
			}
		}));
	}

	function save() {
		try {
			const serializableNodes = nodes.map((n) => {
				const { onUpdate, ...restData } = (n.data ?? {}) as Record<string, unknown>;
				return { ...n, data: restData };
			});
			localStorage.setItem(STORAGE_KEY, JSON.stringify({ nodes: serializableNodes, edges, viewport, showAllNotes }));
		} catch {
			error = 'Could not save whiteboard (storage full)';
		}
	}

	function load() {
		try {
			const raw = localStorage.getItem(STORAGE_KEY);
			if (raw) {
				const data = JSON.parse(raw);
				showAllNotes = Boolean(data.showAllNotes);
				nodes = attachNodeCallbacks(data.nodes || []);
				edges = (data.edges || []).map((e: Edge) => ({
					...e,
					type: 'dashed',
					data: { lineType: e.data?.lineType ?? 'solid', ...e.data }
				}));
				if (data.viewport) viewport = data.viewport;
			}
		} catch {
			error = 'Could not load whiteboard';
		}
	}

	$effect(() => {
		const _n = nodes;
		const _e = edges;
		if (!_n && !_e) return;
		if (autoSaveTimer) clearTimeout(autoSaveTimer);
		autoSaveTimer = setTimeout(save, 1000);
	});

	onMount(() => load());
	onDestroy(() => {
		save();
		if (autoSaveTimer) clearTimeout(autoSaveTimer);
	});

	function nextPosition(index: number) {
		const col = index % 4;
		const row = Math.floor(index / 4);
		return { x: 80 + col * 150, y: 120 + row * 120 };
	}

	function addNode(type: string, label: string, shapeOverride?: string) {
		const id = `node_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
		const pos = nextPosition(nodes.length);
		const shape = shapeOverride ?? selectedNodeShape;
		const baseData =
			type === 'note'
				? { text: label }
				: { shape, label: label || '', note: '' };
		const node: Node = {
			id,
			type,
			position: pos,
			data: {
				...baseData,
				showNotes: showAllNotes,
				onUpdate: (patch: { label?: string; note?: string }) => patchNodeData(id, patch)
			}
		};
		nodes = [...nodes, node];
		toolbarOpen = false;
		toolbarMenuOpen = false;
		connectionMode = false;
		connectFromId = null;
		selectedId = id;
		selectedEdgeId = null;
		if (type === 'shape') selectedNodeShape = shape;
		save();
	}

	function toggleShowAllNotes() {
		showAllNotes = !showAllNotes;
		nodes = nodes.map((n) => ({
			...n,
			data: { ...n.data, showNotes: showAllNotes }
		}));
		save();
	}

	function updateSelected() {
		if (!selectedId) return;
		nodes = nodes.map((n) =>
			n.id === selectedId
				? {
						...n,
						data: {
							...n.data,
							shape: selectedNodeShape,
							label: n.data?.label && n.data?.label !== '' ? n.data?.label : ''
						}
					}
				: n
		);
		save();
	}

	function buildEdge(source: string, target: string, sourceHandle?: string | null, targetHandle?: string | null): Edge {
		return {
			id: `edge_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
			source,
			target,
			sourceHandle: sourceHandle ?? null,
			targetHandle: targetHandle ?? null,
			type: 'dashed',
			data: { lineType: edgeLineType }
		};
	}

	function onConnect(conn: Connection) {
		if (!conn.source || !conn.target) return;
		edges = [...edges, buildEdge(conn.source, conn.target, conn.sourceHandle, conn.targetHandle)];
		connectFromId = null;
		save();
	}

	function getNodeIdFromTarget(target: EventTarget | null): string | null {
		const el = target instanceof Element ? target.closest('.svelte-flow__node') : null;
		return el?.getAttribute('data-id') ?? null;
	}

	function isHandleTarget(target: EventTarget | null): boolean {
		return target instanceof Element && Boolean(target.closest('.svelte-flow__handle'));
	}

	function handleCanvasPointerDown(e: PointerEvent) {
		if (!connectionMode || isHandleTarget(e.target)) {
			pointerDownNodeId = null;
			return;
		}
		pointerDownNodeId = getNodeIdFromTarget(e.target);
	}

	function handleCanvasPointerUp(e: PointerEvent) {
		if (!connectionMode || isHandleTarget(e.target)) {
			pointerDownNodeId = null;
			return;
		}
		const hitEl =
			(e.clientX !== 0 || e.clientY !== 0) && typeof document !== 'undefined'
				? document.elementFromPoint(e.clientX, e.clientY)
				: null;
		const upNodeId = getNodeIdFromTarget(hitEl) ?? getNodeIdFromTarget(e.target);
		const downNodeId = pointerDownNodeId;
		pointerDownNodeId = null;

		if (!upNodeId) return;

		// Dragged from one node onto another node
		if (downNodeId && downNodeId !== upNodeId) {
			edges = [...edges, buildEdge(downNodeId, upNodeId)];
			connectFromId = null;
			save();
			return;
		}

		// Two-click connection: first node -> second node
		if (!connectFromId) {
			connectFromId = upNodeId;
			selectedId = upNodeId;
			return;
		}
		if (connectFromId !== upNodeId) {
			edges = [...edges, buildEdge(connectFromId, upNodeId)];
			connectFromId = null;
			save();
		}
	}

	function handleNodeClick({ node }: { node: Node; event: MouseEvent | TouchEvent }) {
		if (connectionMode) return;
		selectedId = node.id;
		selectedEdgeId = null;
		if (node.type === 'shape' && typeof node.data?.shape === 'string') {
			selectedNodeShape = node.data.shape;
		}
	}

	function handleEdgeClick({ edge }: { edge: Edge; event: MouseEvent }) {
		selectedEdgeId = edge.id;
		selectedId = null;
		connectionMode = false;
		connectFromId = null;
		const lt = edge.data?.lineType as 'solid' | 'dash' | 'dot' | 'solid-dashed' | undefined;
		if (lt && LINE_TYPES.some((t) => t.id === lt)) {
			edgeLineType = lt;
		}
	}

	function handlePaneClick() {
		selectedId = null;
		selectedEdgeId = null;
		connectionMode = false;
		connectFromId = null;
		toolbarOpen = false;
		toolbarMenuOpen = false;
		lineTypeMenuOpen = false;
	}

	function deleteSelected() {
		if (selectedEdgeId) {
			edges = edges.filter((e) => e.id !== selectedEdgeId);
			selectedEdgeId = null;
			save();
			return;
		}
		if (!selectedId) return;
		nodes = nodes.filter((n) => n.id !== selectedId);
		edges = edges.filter((e) => e.source !== selectedId && e.target !== selectedId);
		if (connectFromId === selectedId) connectFromId = null;
		selectedId = null;
		save();
	}

	function zoomIn() {
		viewport = { ...viewport, zoom: Math.min(2, viewport.zoom * 1.2) };
	}

	function zoomOut() {
		viewport = { ...viewport, zoom: Math.max(0.5, viewport.zoom / 1.2) };
	}

	function fitView() {
		viewport = { x: 0, y: 0, zoom: 1 };
	}
</script>

<AppShell title="Board">
	<div class="whiteboard-page" bind:this={canvasEl}>
		<!-- Toolbar -->
		<div class="toolbar">
			<div class="toolbar-btns">
				<!-- Add node menu -->
				<div class="relative">
					<button type="button" class="toolbar-btn" title="Add node" onclick={() => (toolbarOpen = !toolbarOpen)}>
						<Plus size={18} />
					</button>
					{#if toolbarOpen}
						<div class="toolbar-menu">
							<div class="toolbar-menu-title">Add node</div>
							<button type="button" class="toolbar-menu-item" onclick={() => addNode('shape', '', 'rectangle')}>
								<Square size={16} /> Rectangle
							</button>
							<button type="button" class="toolbar-menu-item" onclick={() => addNode('shape', '', 'circle')}>
								<Circle size={16} /> Circle
							</button>
							<button type="button" class="toolbar-menu-item" onclick={() => addNode('shape', '', 'triangle')}>
								<Triangle size={16} /> Triangle
							</button>
							<button type="button" class="toolbar-menu-item" onclick={() => addNode('shape', '', 'arrow')}>
								<ArrowRight size={16} /> Arrow
							</button>
							<button type="button" class="toolbar-menu-item" onclick={() => addNode('note', 'Note')}>
								<Type size={16} /> Note
							</button>
						</div>
					{/if}
				</div>

				<!-- Shape selector (when shape node selected) -->
				{#if selectedId && nodes.find((n) => n.id === selectedId)?.type === 'shape'}
					<div class="relative">
						<button type="button" class="toolbar-btn" title="Shape type" onclick={() => (toolbarMenuOpen = !toolbarMenuOpen)}>
							{#if selectedNodeShape === 'rectangle'}
								<Square size={18} />
							{:else if selectedNodeShape === 'circle'}
								<Circle size={18} />
							{:else if selectedNodeShape === 'triangle'}
								<Triangle size={18} />
							{:else}
								<ArrowRight size={18} />
							{/if}
						</button>
						{#if toolbarMenuOpen}
							<div class="toolbar-menu">
								<button type="button" class="toolbar-menu-item" onclick={() => { selectedNodeShape = 'rectangle'; updateSelected(); toolbarMenuOpen = false; }}>
									<Square size={16} /> Rectangle
								</button>
								<button type="button" class="toolbar-menu-item" onclick={() => { selectedNodeShape = 'circle'; updateSelected(); toolbarMenuOpen = false; }}>
									<Circle size={16} /> Circle
								</button>
								<button type="button" class="toolbar-menu-item" onclick={() => { selectedNodeShape = 'triangle'; updateSelected(); toolbarMenuOpen = false; }}>
									<Triangle size={16} /> Triangle
								</button>
								<button type="button" class="toolbar-menu-item" onclick={() => { selectedNodeShape = 'arrow'; updateSelected(); toolbarMenuOpen = false; }}>
									<ArrowRight size={16} /> Arrow
								</button>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Line style selector (shows current style preview + activates connection mode) -->
				<div class="relative">
					<button
						type="button"
						class="toolbar-btn {connectionMode ? 'active' : ''}"
						title="Line style"
						aria-label="Line style"
						aria-pressed={connectionMode}
						onclick={() => (lineTypeMenuOpen = !lineTypeMenuOpen)}
					>
						<svg width="22" height="10" viewBox="0 0 22 10" aria-hidden="true">
							<line
								x1="1"
								y1="5"
								x2="21"
								y2="5"
								stroke="currentColor"
								stroke-width="2"
								stroke-dasharray={LINE_TYPES.find((t) => t.id === edgeLineType)?.dasharray || undefined}
							/>
						</svg>
					</button>
					{#if lineTypeMenuOpen}
						<div class="toolbar-menu">
							<div class="toolbar-menu-title">Line style</div>
							{#each LINE_TYPES as lt (lt.id)}
								<button
									type="button"
									class="toolbar-menu-item {edgeLineType === lt.id && connectionMode ? 'active-item' : ''}"
									onclick={() => selectLineType(lt.id)}
								>
									<svg width="28" height="12" viewBox="0 0 28 12" aria-hidden="true">
										<line
											x1="1"
											y1="6"
											x2="27"
											y2="6"
											stroke="currentColor"
											stroke-width="2"
											stroke-dasharray={lt.dasharray || undefined}
										/>
									</svg>
									<span>{lt.label}</span>
								</button>
							{/each}
						</div>
					{/if}
				</div>

				<!-- Delete selected -->
				<button type="button" class="toolbar-btn" title="Delete selected" onclick={deleteSelected}>
					<Trash2 size={18} />
				</button>

				<!-- Show notes selector -->
				<button
					type="button"
					class="toolbar-btn {showAllNotes ? 'active' : ''}"
					title="Show notes"
					aria-label="Show notes"
					aria-pressed={showAllNotes}
					onclick={toggleShowAllNotes}
				>
					<StickyNote size={18} />
				</button>

				<!-- Zoom -->
				<button type="button" class="toolbar-btn" title="Zoom in" onclick={zoomIn}>
					<ZoomIn size={18} />
				</button>
				<button type="button" class="toolbar-btn" title="Zoom out" onclick={zoomOut}>
					<ZoomOut size={18} />
				</button>
				<button type="button" class="toolbar-btn" title="Fit view" onclick={fitView}>
					<Minimize size={18} />
				</button>
			</div>

			{#if connectionMode}
				<div class="toolbar-hint">
					{connectFromId ? 'Click target node to link' : 'Click first node to link'}
				</div>
			{:else if selectedNode && selectedNode.type === 'shape'}
				<div class="node-inspector">
					<input
						type="text"
						class="node-inspector-input"
						aria-label="Shape label"
						placeholder="Label"
						value={String(selectedNode.data?.label ?? '')}
						oninput={(e) => patchNodeData(selectedNode.id, { label: e.currentTarget.value })}
					/>
					<input
						type="text"
						class="node-inspector-input"
						aria-label="Shape note"
						placeholder="Add note..."
						value={String(selectedNode.data?.note ?? '')}
						oninput={(e) => patchNodeData(selectedNode.id, { note: e.currentTarget.value })}
					/>
				</div>
			{/if}
		</div>

		<!-- Canvas -->
		<div
			class="canvas-wrapper"
			role="presentation"
			onpointerdown={handleCanvasPointerDown}
			onpointerup={handleCanvasPointerUp}
		>
			<SvelteFlow
				bind:viewport
				bind:nodes
				bind:edges
				{nodeTypes}
				{edgeTypes}
				onconnect={onConnect}
				onnodeclick={handleNodeClick}
				onedgeclick={handleEdgeClick}
				onpaneclick={handlePaneClick}
				nodesDraggable={!connectionMode}
				panOnDrag={!connectionMode}
				nodeClickDistance={5}
				clickConnect={true}
				connectionMode={ConnectionMode.Loose}
				defaultEdgeOptions={{
					type: 'dashed',
					data: { lineType: edgeLineType }
				}}
				proOptions={{ hideAttribution: true }}
			>
				<Background bgColor="var(--surface)" patternColor="var(--border)" />
			</SvelteFlow>
		</div>

		{#if error}
			<p class="error" role="alert">{error}</p>
		{/if}
	</div>
</AppShell>

<style>
	.whiteboard-page {
		position: relative;
		width: 100%;
		height: calc(100dvh - 8.5rem);
		min-height: 400px;
	}

	.toolbar {
		position: absolute;
		top: .75rem;
		left: 50%;
		transform: translateX(-50%);
		z-index: 20;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: .35rem;
		overflow: visible;
	}

	.toolbar-btns {
		display: flex;
		gap: .25rem;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: .5rem;
		padding: .25rem;
		box-shadow: 0 4px 12px rgba(0,0,0,.2);
		overflow: visible;
		justify-content: center;
	}

	.toolbar-hint {
		font-size: .75rem;
		padding: .3rem .6rem;
		border-radius: .375rem;
		background: var(--surface);
		border: 1px solid var(--accent);
		color: var(--text);
		box-shadow: 0 2px 8px rgba(0,0,0,.15);
	}

	.toolbar-btn {
		width: 36px;
		height: 36px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		border-radius: .375rem;
		background: transparent;
		color: var(--text);
		cursor: pointer;
		transition: background .15s;
	}
	.toolbar-btn:hover { background: var(--border); }
	.toolbar-btn.active { background: var(--accent); color: var(--accent-text); }

	.toolbar-menu {
		position: absolute;
		top: 100%;
		left: 0;
		margin-top: .25rem;
		z-index: 30;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: .5rem;
		padding: .5rem;
		min-width: 150px;
		box-shadow: 0 8px 24px rgba(0,0,0,.25);
	}

	.toolbar-menu-title {
		font-size: .7rem;
		font-weight: 600;
		color: var(--muted);
		text-transform: uppercase;
		letter-spacing: .05em;
		padding: .25rem .5rem;
	}

	.toolbar-menu-item {
		display: flex;
		align-items: center;
		gap: .5rem;
		width: 100%;
		padding: .4rem .5rem;
		border: none;
		border-radius: .375rem;
		background: transparent;
		color: var(--text);
		font-size: .85rem;
		cursor: pointer;
		text-align: left;
	}
	.toolbar-menu-item:hover { background: var(--border); }
	.toolbar-menu-item.active-item { background: var(--accent); color: var(--accent-text); }

	.canvas-wrapper {
		width: 100%;
		height: 100%;
		border-radius: 8px;
		overflow: hidden;
	}

	.error {
		position: absolute;
		bottom: 1rem;
		left: 50%;
		transform: translateX(-50%);
		color: var(--danger);
		font-size: .85rem;
	}

	:global(.svelte-flow__node) { cursor: move; }
	:global(.svelte-flow__edge-path) { stroke: var(--accent, #3b82f6); stroke-width: 2; }
	:global(.svelte-flow__handle) {
		width: 10px;
		height: 10px;
		background: var(--accent);
		border: 2px solid var(--surface);
	}

	.node-inspector {
		display: flex;
		flex-wrap: wrap;
		gap: .35rem;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: .5rem;
		padding: .35rem;
		box-shadow: 0 4px 12px rgba(0,0,0,.2);
	}

	.node-inspector-input {
		font-size: .75rem;
		padding: .3rem .5rem;
		border: 1px solid var(--border);
		border-radius: .375rem;
		background: var(--bg);
		color: var(--text);
		min-width: 120px;
	}
	.node-inspector-input:focus {
		outline: 1.5px solid var(--accent);
		border-color: var(--accent);
	}
</style>
