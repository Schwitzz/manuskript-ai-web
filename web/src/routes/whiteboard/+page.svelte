<script lang="ts">
	import '@xyflow/svelte/dist/style.css';
	import AppShell from '#lib/components/AppShell.svelte';
	import { project } from '#lib/stores/project.svelte.ts';
	import { onMount, onDestroy } from 'svelte';
	import {
		SvelteFlow,
		Background,
		ConnectionMode,
		MarkerType,
		type Connection,
		type Node,
		type Edge,
		type NodeTypes,
		type Viewport
	} from '@xyflow/svelte';
	import {
		Square, Circle, Triangle, ArrowRight, Minus,
		Type, Sparkles, Scissors, Layers, Link,
		Map, Book, Flag, Eye, Clock, Compass,
		Globe, Mountain, Sun, Cloud, Wind,
		Flame, Droplets, Trash2, Plus,
		Minimize, ZoomIn, ZoomOut
	} from '@lucide/svelte';
	import ShapeNode from './ShapeNode.svelte';
	import IconNode from './IconNode.svelte';
	import NoteNode from './NoteNode.svelte';

	const PROJECT = project.name || 'whiteboard';
	const STORAGE_KEY = `msk_whiteboard_${PROJECT}`;

	const nodeTypes: NodeTypes = {
		shape: ShapeNode as unknown as NodeTypes['shape'],
		icon: IconNode as unknown as NodeTypes['icon'],
		note: NoteNode as unknown as NodeTypes['note']
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
	let edgeArrow = $state(true);
	let selectedNodeShape = $state('rectangle');
	let selectedNodeIcon = $state('Sparkles');
	let error = $state('');
	let viewport = $state<Viewport>({ x: 0, y: 0, zoom: 1 });
	let autoSaveTimer: ReturnType<typeof setTimeout> | null = null;

	function save() {
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify({ nodes, edges, viewport }));
		} catch {
			error = 'Could not save whiteboard (storage full)';
		}
	}

	function load() {
		try {
			const raw = localStorage.getItem(STORAGE_KEY);
			if (raw) {
				const data = JSON.parse(raw);
				nodes = data.nodes || [];
				edges = data.edges || [];
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
		return { x: 100 + col * 150, y: 100 + row * 120 };
	}

	function addNode(type: string, label: string, shapeOverride?: string) {
		const id = `node_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
		const pos = nextPosition(nodes.length);
		const shape = shapeOverride ?? selectedNodeShape;
		const node: Node = {
			id,
			type,
			position: pos,
			data:
				type === 'icon'
					? { icon: selectedNodeIcon, label }
					: type === 'note'
						? { text: label }
						: { shape, label }
		};
		nodes = [...nodes, node];
		toolbarOpen = false;
		toolbarMenuOpen = false;
		iconPickerOpen = false;
		selectedId = id;
		selectedEdgeId = null;
		if (type === 'shape') selectedNodeShape = shape;
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
							label:
								n.data?.label === 'Shape' ||
								n.data?.label === 'Rectangle' ||
								n.data?.label === 'Circle' ||
								n.data?.label === 'Triangle' ||
								n.data?.label === 'Arrow'
									? selectedNodeShape === 'rectangle'
										? 'Shape'
										: selectedNodeShape.charAt(0).toUpperCase() + selectedNodeShape.slice(1)
									: n.data?.label
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
			type: 'default',
			style: 'stroke: var(--accent); stroke-width: 2px;',
			markerEnd: edgeArrow ? { type: MarkerType.ArrowClosed, color: 'var(--accent)' } : undefined
		};
	}

	function onConnect(conn: Connection) {
		if (!conn.source || !conn.target) return;
		edges = [...edges, buildEdge(conn.source, conn.target, conn.sourceHandle, conn.targetHandle)];
		connectFromId = null;
		save();
	}

	function handleNodeClick({ node }: { node: Node; event: MouseEvent | TouchEvent }) {
		if (connectionMode) {
			if (!connectFromId) {
				connectFromId = node.id;
				selectedId = node.id;
				return;
			}
			if (connectFromId !== node.id) {
				edges = [...edges, buildEdge(connectFromId, node.id)];
				connectFromId = null;
				save();
				return;
			}
		}
		selectedId = node.id;
		selectedEdgeId = null;
		if (node.type === 'shape' && typeof node.data?.shape === 'string') {
			selectedNodeShape = node.data.shape;
		} else if (node.type === 'icon' && typeof node.data?.icon === 'string') {
			selectedNodeIcon = node.data.icon;
		}
	}

	function handleEdgeClick({ edge }: { edge: Edge; event: MouseEvent }) {
		selectedEdgeId = edge.id;
		selectedId = null;
	}

	function handlePaneClick() {
		selectedId = null;
		selectedEdgeId = null;
		connectFromId = null;
		toolbarOpen = false;
		toolbarMenuOpen = false;
		iconPickerOpen = false;
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

	function toggleConnectionMode() {
		connectionMode = !connectionMode;
		connectFromId = null;
	}

	let iconPickerOpen = $state(false);
	const iconMap: Record<string, typeof Sparkles> = {
		Sparkles, Type, Notebook: Sparkles, Scissors, Layers, Link,
		Map, Book, Flag, Eye, Clock, Compass,
		Globe, Mountain, Sun, Cloud, Wind,
		Flame, Droplets, Trash2, Plus, Square, Circle, Triangle, ArrowRight
	};
	const iconNames = Object.keys(iconMap);

	function selectIcon(name: string) {
		selectedNodeIcon = name;
		if (selectedId) {
			nodes = nodes.map((n) =>
				n.id === selectedId ? { ...n, data: { ...n.data, icon: name, label: name } } : n
			);
			save();
		}
		iconPickerOpen = false;
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
							<button type="button" class="toolbar-menu-item" onclick={() => addNode('shape', 'Shape', 'rectangle')}>
								<Square size={16} /> Shape
							</button>
							<button type="button" class="toolbar-menu-item" onclick={() => addNode('shape', 'Circle', 'circle')}>
								<Circle size={16} /> Circle
							</button>
							<button type="button" class="toolbar-menu-item" onclick={() => addNode('shape', 'Triangle', 'triangle')}>
								<Triangle size={16} /> Triangle
							</button>
							<button type="button" class="toolbar-menu-item" onclick={() => addNode('shape', 'Arrow', 'arrow')}>
								<ArrowRight size={16} /> Arrow
							</button>
							<button type="button" class="toolbar-menu-item" onclick={() => addNode('icon', 'Icon')}>
								<Sparkles size={16} /> Icon
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

				<!-- Icon selector (when icon node selected) -->
				{#if selectedId && nodes.find((n) => n.id === selectedId)?.type === 'icon'}
					<div class="relative">
						<button type="button" class="toolbar-btn" title="Icon" onclick={() => (iconPickerOpen = !iconPickerOpen)}>
							<Sparkles size={18} />
						</button>
						{#if iconPickerOpen}
							<div class="toolbar-menu icon-picker">
								{#each iconNames as name}
									{@const Comp = iconMap[name]}
									<button type="button" class="icon-picker-btn" onclick={() => selectIcon(name)} title={name}>
										<Comp size={16} />
									</button>
								{/each}
							</div>
						{/if}
					</div>
				{/if}

				<!-- Connection mode (click two nodes or drag between handles) -->
				<button type="button" class="toolbar-btn {connectionMode ? 'active' : ''}" title="Connection mode" onclick={toggleConnectionMode}>
					<Link size={18} />
				</button>

				<!-- Connector style: Arrow vs Line -->
				<button
					type="button"
					class="toolbar-btn"
					title={edgeArrow ? 'Connector: Arrow (click for Line)' : 'Connector: Line (click for Arrow)'}
					onclick={() => (edgeArrow = !edgeArrow)}
				>
					{#if edgeArrow}
						<ArrowRight size={18} />
					{:else}
						<Minus size={18} />
					{/if}
				</button>

				<!-- Delete selected -->
				<button type="button" class="toolbar-btn" title="Delete selected" onclick={deleteSelected}>
					<Trash2 size={18} />
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
					{connectFromId ? 'Click target node to link' : 'Click first node (or drag between handles)'}
				</div>
			{/if}
		</div>

		<!-- Canvas -->
		<div class="canvas-wrapper">
			<SvelteFlow
				bind:viewport
				bind:nodes
				bind:edges
				{nodeTypes}
				onconnect={onConnect}
				onnodeclick={handleNodeClick}
				onedgeclick={handleEdgeClick}
				onpaneclick={handlePaneClick}
				clickConnect={true}
				connectionMode={ConnectionMode.Loose}
				defaultEdgeOptions={{
					type: 'default',
					style: 'stroke: var(--accent); stroke-width: 2px;',
					markerEnd: edgeArrow ? { type: MarkerType.ArrowClosed, color: 'var(--accent)' } : undefined
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
		left: .75rem;
		z-index: 20;
		display: flex;
		flex-direction: column;
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

	.icon-picker {
		display: grid;
		grid-template-columns: repeat(5, 1fr);
		gap: .25rem;
	}
	.icon-picker-btn {
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
	}
	.icon-picker-btn:hover { background: var(--border); }

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
	:global(.svelte-flow__edge-path) { stroke-width: 2; }
	:global(.svelte-flow__handle) {
		width: 10px;
		height: 10px;
		background: var(--accent);
		border: 2px solid var(--surface);
	}
</style>
