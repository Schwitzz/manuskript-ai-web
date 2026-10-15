<script lang="ts">
	import '@xyflow/svelte/dist/style.css';
	import AppShell from '#lib/components/AppShell.svelte';
	import { project } from '#lib/stores/project.svelte.ts';
	import { call } from '#lib/api';
	import type { WhiteboardBoard, WhiteboardsData } from '#lib/api-types';
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
		Minimize, ZoomIn, ZoomOut, StickyNote,
		Palette, Layers, Pencil, Check
	} from '@lucide/svelte';
	import { LINE_TYPES } from '#lib/whiteboard/line-types';
	import { WHITEBOARD_COLORS } from '#lib/whiteboard/colors';
	import ShapeNode from './ShapeNode.svelte';
	import NoteNode from './NoteNode.svelte';
	import DashedEdge from './DashedEdge.svelte';

	const PROJECT = project.name || 'whiteboard';
	const STORAGE_KEY = `msk_whiteboard_${PROJECT}`;
	const MULTI_STORAGE_KEY = `msk_whiteboards_${PROJECT}`;

	const nodeTypes: NodeTypes = {
		shape: ShapeNode as unknown as NodeTypes['shape'],
		note: NoteNode as unknown as NodeTypes['note']
	};

	const edgeTypes = {
		dashed: DashedEdge
	};

	interface BoardEntry {
		id: string;
		name: string;
		nodes: Node[];
		edges: Edge[];
		viewport: Viewport;
		show_all_notes: boolean;
	}

	let canvasEl: HTMLDivElement | undefined = $state();
	let boards = $state<BoardEntry[]>([
		{
			id: 'default',
			name: 'Main Board',
			nodes: [],
			edges: [],
			viewport: { x: 0, y: 0, zoom: 1 },
			show_all_notes: false
		}
	]);
	let activeBoardId = $state('default');
	let nodes = $state<Node[]>([]);
	let edges = $state<Edge[]>([]);
	let selectedId = $state<string | null>(null);
	let selectedEdgeId = $state<string | null>(null);
	let toolbarOpen = $state(false);
	let toolbarMenuOpen = $state(false);
	let boardMenuOpen = $state(false);
	let colorMenuOpen = $state(false);
	let connectionMode = $state(false);
	let connectFromId = $state<string | null>(null);
	let pointerDownNodeId = $state<string | null>(null);
	let selectedNodeShape = $state('rectangle');
	let edgeLineType = $state<'solid' | 'dash' | 'dot' | 'solid-dashed'>('solid');
	let activeColor = $state('');
	let showAllNotes = $state(false);
	let lineTypeMenuOpen = $state(false);

	// Board create/rename inline state
	let boardAction = $state<'create' | 'rename' | null>(null);
	let boardNameDraft = $state('');

	const activeBoard = $derived(boards.find((b) => b.id === activeBoardId) ?? boards[0]);
	const selectedNode = $derived(selectedId ? (nodes.find((n) => n.id === selectedId) ?? null) : null);
	const selectedEdge = $derived(selectedEdgeId ? (edges.find((e) => e.id === selectedEdgeId) ?? null) : null);
	const currentColorDisplay = $derived.by(() => {
		if (selectedNode) return String(selectedNode.data?.color ?? '');
		if (selectedEdge) return String(selectedEdge.data?.color ?? '');
		return activeColor;
	});

	function closeAllMenus() {
		toolbarOpen = false;
		toolbarMenuOpen = false;
		lineTypeMenuOpen = false;
		colorMenuOpen = false;
		boardMenuOpen = false;
		boardAction = null;
	}

	function selectLineType(lineType: 'solid' | 'dash' | 'dot' | 'solid-dashed') {
		edgeLineType = lineType;
		lineTypeMenuOpen = false;
		if (selectedEdgeId) {
			edges = edges.map((e) =>
				e.id === selectedEdgeId
					? { ...e, type: 'dashed', data: { ...e.data, lineType } }
					: e
			);
			void save();
		}
		connectionMode = true;
		connectFromId = null;
	}

	function selectColor(colorValue: string) {
		activeColor = colorValue;
		colorMenuOpen = false;
		if (selectedId) {
			patchNodeData(selectedId, { color: colorValue });
			return;
		}
		if (selectedEdgeId) {
			edges = edges.map((e) =>
				e.id === selectedEdgeId
					? { ...e, type: 'dashed', data: { ...e.data, color: colorValue } }
					: e
			);
			void save();
		}
	}

	let error = $state('');
	let viewport = $state<Viewport>({ x: 0, y: 0, zoom: 1 });
	let autoSaveTimer: ReturnType<typeof setTimeout> | null = null;
	let loadedOnce = $state(false);

	function patchNodeData(nodeId: string, patch: { label?: string; note?: string; text?: string; color?: string }) {
		nodes = nodes.map((n) =>
			n.id === nodeId
				? { ...n, data: { ...n.data, ...patch } }
				: n
		);
		void save();
	}

	function attachNodeCallbacks(rawNodes: Node[], showNotesFlag = showAllNotes): Node[] {
		return rawNodes.map((n) => ({
			...n,
			data: {
				...n.data,
				showNotes: showNotesFlag,
				onUpdate: (patch: { label?: string; note?: string; text?: string; color?: string }) =>
					patchNodeData(n.id, patch)
			}
		}));
	}

	function serializeNodes(rawNodes: Node[]): Record<string, unknown>[] {
		return rawNodes.map((n) => {
			const { onUpdate, ...restData } = (n.data ?? {}) as Record<string, unknown>;
			return { ...n, data: restData };
		});
	}

	function syncActiveBoardState() {
		boards = boards.map((b) =>
			b.id === activeBoardId
				? {
						...b,
						nodes: serializeNodes(nodes) as unknown as Node[],
						edges,
						viewport,
						show_all_notes: showAllNotes
					}
				: b
		);
	}

	function applyBoardToCanvas(board: BoardEntry) {
		activeBoardId = board.id;
		showAllNotes = Boolean(board.show_all_notes);
		nodes = attachNodeCallbacks(board.nodes || [], showAllNotes);
		edges = (board.edges || []).map((e: Edge) => ({
			...e,
			type: 'dashed',
			data: { lineType: e.data?.lineType ?? 'solid', color: e.data?.color ?? '', ...e.data }
		}));
		viewport = board.viewport ?? { x: 0, y: 0, zoom: 1 };
		selectedId = null;
		selectedEdgeId = null;
		connectionMode = false;
		connectFromId = null;
	}

	function buildPayload(): WhiteboardsData {
		syncActiveBoardState();
		return {
			active_board_id: activeBoardId,
			boards: boards.map((b) => ({
				id: b.id,
				name: b.name,
				nodes: (b.id === activeBoardId ? serializeNodes(nodes) : serializeNodes(b.nodes)) as Record<string, unknown>[],
				edges: (b.id === activeBoardId ? edges : b.edges) as unknown as Record<string, unknown>[],
				viewport: b.id === activeBoardId ? viewport : b.viewport,
				show_all_notes: b.id === activeBoardId ? showAllNotes : b.show_all_notes
			}))
		};
	}

	async function save() {
		const payload = buildPayload();
		try {
			localStorage.setItem(MULTI_STORAGE_KEY, JSON.stringify(payload));
			// Also mirror active board to legacy key for backwards compatibility
			const current = payload.boards.find((b) => b.id === payload.active_board_id) ?? payload.boards[0];
			if (current) {
				localStorage.setItem(
					STORAGE_KEY,
					JSON.stringify({
						nodes: current.nodes,
						edges: current.edges,
						viewport: current.viewport,
						showAllNotes: current.show_all_notes
					})
				);
			}
		} catch {
			error = 'Could not save whiteboard (storage full)';
		}
		if (project.name) {
			try {
				await call('PUT /api/projects/{name}/whiteboards', {
					params: { name: project.name },
					body: payload
				});
			} catch {
				// Offline or unauthenticated fallback already saved to localStorage
			}
		}
	}

	function hydrateFromPayload(data: WhiteboardsData) {
		if (!data.boards || data.boards.length === 0) return;
		boards = data.boards.map((b: WhiteboardBoard) => ({
			id: b.id,
			name: b.name,
			nodes: (b.nodes ?? []) as unknown as Node[],
			edges: (b.edges ?? []) as unknown as Edge[],
			viewport: {
				x: b.viewport?.x ?? 0,
				y: b.viewport?.y ?? 0,
				zoom: b.viewport?.zoom ?? 1
			},
			show_all_notes: Boolean(b.show_all_notes)
		}));
		const target = boards.find((b) => b.id === data.active_board_id) ?? boards[0];
		applyBoardToCanvas(target);
	}

	async function load() {
		try {
			if (project.name) {
				try {
					const serverData = await call('GET /api/projects/{name}/whiteboards', {
						params: { name: project.name }
					});
					const hasServerContent = serverData.boards.some(
						(b) => (b.nodes && b.nodes.length > 0) || (b.edges && b.edges.length > 0) || serverData.boards.length > 1
					);
					if (hasServerContent) {
						hydrateFromPayload(serverData);
						loadedOnce = true;
						return;
					}
				} catch {
					// Fall back to localStorage below
				}
			}

			const multiRaw = localStorage.getItem(MULTI_STORAGE_KEY);
			if (multiRaw) {
				const parsed = JSON.parse(multiRaw) as WhiteboardsData;
				hydrateFromPayload(parsed);
				loadedOnce = true;
				if (project.name) void save();
				return;
			}

			const legacyRaw = localStorage.getItem(STORAGE_KEY);
			if (legacyRaw) {
				const data = JSON.parse(legacyRaw);
				const migrated: WhiteboardsData = {
					active_board_id: 'default',
					boards: [
						{
							id: 'default',
							name: 'Main Board',
							nodes: data.nodes || [],
							edges: data.edges || [],
							viewport: data.viewport || { x: 0, y: 0, zoom: 1 },
							show_all_notes: Boolean(data.showAllNotes)
						}
					]
				};
				hydrateFromPayload(migrated);
				loadedOnce = true;
				void save();
				return;
			}
			loadedOnce = true;
		} catch {
			error = 'Could not load whiteboard';
			loadedOnce = true;
		}
	}

	function switchBoard(id: string) {
		if (id === activeBoardId) {
			boardMenuOpen = false;
			return;
		}
		syncActiveBoardState();
		const next = boards.find((b) => b.id === id);
		if (next) {
			applyBoardToCanvas(next);
			boardMenuOpen = false;
			boardAction = null;
			void save();
		}
	}

	function startCreateBoard() {
		boardAction = 'create';
		boardNameDraft = `Board ${boards.length + 1}`;
	}

	function startRenameBoard() {
		boardAction = 'rename';
		boardNameDraft = activeBoard?.name ?? 'Main Board';
	}

	function confirmBoardAction() {
		const clean = boardNameDraft.trim();
		if (!clean) return;
		if (boardAction === 'create') {
			syncActiveBoardState();
			const id = `board_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
			const newBoard: BoardEntry = {
				id,
				name: clean,
				nodes: [],
				edges: [],
				viewport: { x: 0, y: 0, zoom: 1 },
				show_all_notes: false
			};
			boards = [...boards, newBoard];
			applyBoardToCanvas(newBoard);
			boardAction = null;
			boardMenuOpen = false;
			void save();
		} else if (boardAction === 'rename') {
			boards = boards.map((b) => (b.id === activeBoardId ? { ...b, name: clean } : b));
			boardAction = null;
			boardMenuOpen = false;
			void save();
		}
	}

	function deleteActiveBoard() {
		if (boards.length <= 1) return;
		const remaining = boards.filter((b) => b.id !== activeBoardId);
		boards = remaining;
		applyBoardToCanvas(remaining[0]);
		boardMenuOpen = false;
		boardAction = null;
		void save();
	}

	$effect(() => {
		const _n = nodes;
		const _e = edges;
		if (!loadedOnce || (!_n && !_e)) return;
		if (autoSaveTimer) clearTimeout(autoSaveTimer);
		autoSaveTimer = setTimeout(() => {
			void save();
		}, 1000);
	});

	onMount(() => {
		void load();
	});
	onDestroy(() => {
		if (loadedOnce) void save();
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
				? { text: label, color: activeColor }
				: { shape, label: label || '', note: '', color: activeColor };
		const node: Node = {
			id,
			type,
			position: pos,
			data: {
				...baseData,
				showNotes: showAllNotes,
				onUpdate: (patch: { label?: string; note?: string; text?: string; color?: string }) =>
					patchNodeData(id, patch)
			}
		};
		nodes = [...nodes, node];
		closeAllMenus();
		connectionMode = false;
		connectFromId = null;
		selectedId = id;
		selectedEdgeId = null;
		if (type === 'shape') selectedNodeShape = shape;
		void save();
	}

	function toggleShowAllNotes() {
		showAllNotes = !showAllNotes;
		nodes = nodes.map((n) => ({
			...n,
			data: { ...n.data, showNotes: showAllNotes }
		}));
		void save();
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
		void save();
	}

	function buildEdge(source: string, target: string, sourceHandle?: string | null, targetHandle?: string | null): Edge {
		return {
			id: `edge_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
			source,
			target,
			sourceHandle: sourceHandle ?? null,
			targetHandle: targetHandle ?? null,
			type: 'dashed',
			data: { lineType: edgeLineType, color: activeColor }
		};
	}

	function onConnect(conn: Connection) {
		if (!conn.source || !conn.target) return;
		edges = [...edges, buildEdge(conn.source, conn.target, conn.sourceHandle, conn.targetHandle)];
		connectFromId = null;
		void save();
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
			void save();
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
			void save();
		}
	}

	function handleNodeClick({ node }: { node: Node; event: MouseEvent | TouchEvent }) {
		if (connectionMode) return;
		selectedId = node.id;
		selectedEdgeId = null;
		if (node.type === 'shape' && typeof node.data?.shape === 'string') {
			selectedNodeShape = node.data.shape;
		}
		if (typeof node.data?.color === 'string') {
			activeColor = node.data.color;
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
		if (typeof edge.data?.color === 'string') {
			activeColor = edge.data.color;
		}
	}

	function handlePaneClick() {
		selectedId = null;
		selectedEdgeId = null;
		connectionMode = false;
		connectFromId = null;
		closeAllMenus();
	}

	function deleteSelected() {
		if (selectedEdgeId) {
			edges = edges.filter((e) => e.id !== selectedEdgeId);
			selectedEdgeId = null;
			void save();
			return;
		}
		if (!selectedId) return;
		nodes = nodes.filter((n) => n.id !== selectedId);
		edges = edges.filter((e) => e.source !== selectedId && e.target !== selectedId);
		if (connectFromId === selectedId) connectFromId = null;
		selectedId = null;
		void save();
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
				<!-- Multi-board selector -->
				<div class="relative">
					<button
						type="button"
						class="toolbar-board-btn"
						title="Switch or manage whiteboards"
						aria-label="Whiteboards"
						onclick={() => {
							const next = !boardMenuOpen;
							closeAllMenus();
							boardMenuOpen = next;
						}}
					>
						<Layers size={16} />
						<span class="toolbar-board-name">{activeBoard?.name ?? 'Main Board'}</span>
					</button>
					{#if boardMenuOpen}
						<div class="toolbar-menu board-menu">
							<div class="toolbar-menu-title">Whiteboards ({boards.length})</div>
							{#each boards as b (b.id)}
								<button
									type="button"
									class="toolbar-menu-item {b.id === activeBoardId ? 'active-item' : ''}"
									onclick={() => switchBoard(b.id)}
								>
									<span class="flex-1 truncate">{b.name}</span>
									{#if b.id === activeBoardId}
										<Check size={14} />
									{/if}
								</button>
							{/each}
							<div class="menu-divider"></div>
							{#if boardAction}
								<div class="board-action-row">
									<input
										type="text"
										class="node-inspector-input"
										aria-label="Board name"
										placeholder="Board name..."
										bind:value={boardNameDraft}
										onkeydown={(e) => {
											if (e.key === 'Enter') confirmBoardAction();
											if (e.key === 'Escape') boardAction = null;
										}}
									/>
									<button
										type="button"
										class="toolbar-btn active"
										title="Save board"
										aria-label="Save board"
										onclick={confirmBoardAction}
									>
										<Check size={15} />
									</button>
								</div>
							{:else}
								<button type="button" class="toolbar-menu-item" onclick={startCreateBoard}>
									<Plus size={15} /> New whiteboard
								</button>
								<button type="button" class="toolbar-menu-item" onclick={startRenameBoard}>
									<Pencil size={15} /> Rename board
								</button>
								{#if boards.length > 1}
									<button type="button" class="toolbar-menu-item danger-item" onclick={deleteActiveBoard}>
										<Trash2 size={15} /> Delete board
									</button>
								{/if}
							{/if}
						</div>
					{/if}
				</div>

				<!-- Add node menu -->
				<div class="relative">
					<button
						type="button"
						class="toolbar-btn"
						title="Add node"
						onclick={() => {
							const next = !toolbarOpen;
							closeAllMenus();
							toolbarOpen = next;
						}}
					>
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
						<button
							type="button"
							class="toolbar-btn"
							title="Shape type"
							onclick={() => {
								const next = !toolbarMenuOpen;
								closeAllMenus();
								toolbarMenuOpen = next;
							}}
						>
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
						onclick={() => {
							const next = !lineTypeMenuOpen;
							closeAllMenus();
							lineTypeMenuOpen = next;
						}}
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

				<!-- Color selector for shapes, notes, and connector lines -->
				<div class="relative">
					<button
						type="button"
						class="toolbar-btn"
						title="Color"
						aria-label="Color"
						onclick={() => {
							const next = !colorMenuOpen;
							closeAllMenus();
							colorMenuOpen = next;
						}}
					>
						<Palette size={18} style="color: {currentColorDisplay || 'var(--accent)'}" />
					</button>
					{#if colorMenuOpen}
						<div class="toolbar-menu color-menu">
							<div class="toolbar-menu-title">Color</div>
							<div class="color-swatches">
								{#each WHITEBOARD_COLORS as c (c.id)}
									<button
										type="button"
										class="color-swatch-btn {currentColorDisplay === c.value ? 'selected' : ''}"
										title={c.label}
										aria-label="Color {c.label}"
										style="background: {c.swatch}"
										onclick={() => selectColor(c.value)}
									></button>
								{/each}
							</div>
							<div class="custom-color-row">
								<label class="custom-color-label" for="wb-custom-color">Custom</label>
								<input
									id="wb-custom-color"
									type="color"
									aria-label="Custom color"
									value={currentColorDisplay && currentColorDisplay.startsWith('#') ? currentColorDisplay : '#3b82f6'}
									oninput={(e) => selectColor(e.currentTarget.value)}
								/>
							</div>
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
					data: { lineType: edgeLineType, color: activeColor }
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
		align-items: center;
	}

	.toolbar-board-btn {
		height: 36px;
		padding: 0 .6rem;
		display: flex;
		align-items: center;
		gap: .4rem;
		border: none;
		border-radius: .375rem;
		background: transparent;
		color: var(--text);
		font-size: .8rem;
		font-weight: 500;
		cursor: pointer;
		transition: background .15s;
		max-width: 150px;
	}
	.toolbar-board-btn:hover { background: var(--border); }

	.toolbar-board-name {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
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

	.board-menu {
		min-width: 210px;
	}

	.color-menu {
		min-width: 176px;
	}

	.color-swatches {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: .4rem;
		padding: .35rem .25rem;
	}

	.color-swatch-btn {
		width: 28px;
		height: 28px;
		border-radius: 9999px;
		border: 2px solid var(--border);
		cursor: pointer;
		transition: transform .1s, border-color .1s;
	}
	.color-swatch-btn:hover {
		transform: scale(1.1);
	}
	.color-swatch-btn.selected {
		border-color: var(--text);
		box-shadow: 0 0 0 2px var(--surface);
	}

	.custom-color-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: .35rem .25rem 0;
		border-top: 1px solid var(--border);
		margin-top: .25rem;
	}

	.custom-color-label {
		font-size: .75rem;
		color: var(--muted);
	}

	.menu-divider {
		height: 1px;
		background: var(--border);
		margin: .35rem 0;
	}

	.board-action-row {
		display: flex;
		align-items: center;
		gap: .25rem;
		padding: .2rem 0;
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
	.toolbar-menu-item.danger-item { color: var(--danger); }

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
