# Chunk 1: Whiteboard Editable Shape Labels & Shape Notes (Hover + Show Notes Selector)

**Status:** ✅ Complete (Tests Passing — 135 unit + 18 E2E + 308 server)

## Implementation Notes (Post-Review Refinements)
- Shapes now start with a **blank label** (`''`) by default instead of `'Shape'`.
- The Add Node menu uses **Rectangle** (instead of `"Shape"`), **Circle**, **Triangle**, **Arrow**, and **Note**.
- `IconNode.svelte` and the icon picker/node type were removed completely.
- The whiteboard toolbar is centered horizontally at the top of the canvas.

## Scope & Context Budget
- **Files to read/edit:**
  1. `web/src/routes/whiteboard/ShapeNode.svelte` (51 lines)
  2. `web/src/routes/whiteboard/IconNode.svelte` (55 lines)
  3. `web/src/routes/whiteboard/+page.svelte` (555 lines)
  4. `web/e2e/project-flow.spec.ts` (169 lines)
- **Estimated token usage:** ~12k tokens (well under 70k limit).

## What This Chunk Implements
1. **Editable names/labels on Whiteboard shapes after adding to board:**
   - Double-clicking a shape's label in `ShapeNode.svelte` opens an inline `<input>` directly on the node that commits via `data.onUpdate({ label })`.
   - Selecting any shape/icon node on the canvas also shows a compact **Label** input and **Note** input in the whiteboard toolbar so mobile/touch users and desktop users can edit the selected shape's name and note anytime.
2. **Whiteboard shape notes (unobtrusive on hover OR via "Show notes" selector):**
   - Each shape/icon node stores `data.note?: string` and receives `data.showNotes?: boolean`.
   - When `data.note` is non-empty, a tiny unobtrusive indicator badge (`.shape-note-badge`) is rendered in the top-right corner of the shape.
   - Hovering over the shape (`.shape-node:hover .shape-note-popover`) OR toggling the toolbar **"Show notes"** button (`showAllNotes` state passed via `data.showNotes`) displays the note unobtrusively above the shape.

---

## Step-by-Step Line Edits

### 1. Edit `web/src/routes/whiteboard/ShapeNode.svelte` (Lines 1–51)

Replace the entire contents of `web/src/routes/whiteboard/ShapeNode.svelte` (lines 1–51):

**`oldString`:**
```svelte
<script lang="ts">
	import { Handle, Position, type Node, type NodeProps } from '@xyflow/svelte';
	import { Square, Circle, Triangle, ArrowRight } from '@lucide/svelte';

	type ShapeNodeType = Node<{ label?: string; shape?: string }, 'shape'>;

	let { data, selected }: NodeProps<ShapeNodeType> = $props();

	const shape = $derived(data?.shape || 'rectangle');
	const label = $derived(data?.label || 'Shape');
</script>

<div class="shape-node {selected ? 'selected' : ''}">
	<Handle type="target" position={Position.Left} />
	{#if shape === 'arrow'}
		<ArrowRight size={32} style="color:var(--accent)" />
	{:else if shape === 'circle'}
		<Circle size={32} style="color:var(--accent)" />
	{:else if shape === 'triangle'}
		<Triangle size={32} style="color:var(--accent)" />
	{:else}
		<Square size={32} style="color:var(--accent)" />
	{/if}
	<span class="shape-label">{label}</span>
	<Handle type="source" position={Position.Right} />
</div>

<style>
	:global(.shape-node) {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
		padding: 12px 18px;
		border-radius: 8px;
		background: var(--surface);
		border: 1.5px solid var(--border);
		cursor: pointer;
		user-select: none;
		min-width: 84px;
	}
	:global(.shape-node.selected) {
		border-color: var(--accent);
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 30%, transparent);
	}
	.shape-label {
		font-size: .75rem;
		color: var(--text);
		text-align: center;
	}
</style>
```

**`newString`:**
```svelte
<script lang="ts">
	import { Handle, Position, type Node, type NodeProps } from '@xyflow/svelte';
	import { Square, Circle, Triangle, ArrowRight, StickyNote } from '@lucide/svelte';

	type ShapeNodeData = {
		label?: string;
		shape?: string;
		note?: string;
		showNotes?: boolean;
		onUpdate?: (patch: { label?: string; note?: string }) => void;
	};
	type ShapeNodeType = Node<ShapeNodeData, 'shape'>;

	let { data, selected }: NodeProps<ShapeNodeType> = $props();

	const shape = $derived(data?.shape || 'rectangle');
	const label = $derived(data?.label || 'Shape');
	const note = $derived(data?.note || '');
	const showNotes = $derived(Boolean(data?.showNotes));

	let editingLabel = $state(false);
	let draftLabel = $state('');

	function startInlineEdit(e: MouseEvent) {
		e.stopPropagation();
		draftLabel = label;
		editingLabel = true;
	}

	function commitInlineEdit() {
		if (!editingLabel) return;
		editingLabel = false;
		const clean = draftLabel.trim() || 'Shape';
		data?.onUpdate?.({ label: clean });
	}
</script>

<div class="shape-node {selected ? 'selected' : ''}">
	<Handle type="target" position={Position.Left} />
	{#if note}
		<span class="shape-note-badge" title="Has note" aria-label="Shape has note">
			<StickyNote size={11} />
		</span>
		<div class="shape-note-popover {showNotes ? 'force-visible' : ''}" role="note">
			{note}
		</div>
	{/if}
	{#if shape === 'arrow'}
		<ArrowRight size={32} style="color:var(--accent)" />
	{:else if shape === 'circle'}
		<Circle size={32} style="color:var(--accent)" />
	{:else if shape === 'triangle'}
		<Triangle size={32} style="color:var(--accent)" />
	{:else}
		<Square size={32} style="color:var(--accent)" />
	{/if}
	{#if editingLabel}
		<input
			type="text"
			class="shape-label-input nodrag"
			aria-label="Shape name"
			bind:value={draftLabel}
			onblur={commitInlineEdit}
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => {
				e.stopPropagation();
				if (e.key === 'Enter') commitInlineEdit();
				if (e.key === 'Escape') editingLabel = false;
			}}
		/>
	{:else}
		<span
			class="shape-label"
			ondblclick={startInlineEdit}
			title="Double-click to rename"
		>{label}</span>
	{/if}
	<Handle type="source" position={Position.Right} />
</div>

<style>
	:global(.shape-node) {
		position: relative;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
		padding: 12px 18px;
		border-radius: 8px;
		background: var(--surface);
		border: 1.5px solid var(--border);
		cursor: pointer;
		user-select: none;
		min-width: 84px;
	}
	:global(.shape-node.selected) {
		border-color: var(--accent);
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 30%, transparent);
	}
	.shape-label {
		font-size: .75rem;
		color: var(--text);
		text-align: center;
		max-width: 140px;
		overflow-wrap: anywhere;
	}
	.shape-label-input {
		width: 96px;
		font-size: .75rem;
		padding: 2px 4px;
		border: 1px solid var(--accent);
		border-radius: 4px;
		background: var(--bg);
		color: var(--text);
		text-align: center;
	}
	.shape-note-badge {
		position: absolute;
		top: 4px;
		right: 4px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		color: var(--accent);
		opacity: 0.75;
	}
	.shape-note-popover {
		position: absolute;
		bottom: calc(100% + 6px);
		left: 50%;
		transform: translateX(-50%);
		z-index: 40;
		min-width: 120px;
		max-width: 220px;
		padding: 6px 8px;
		border-radius: 6px;
		background: var(--surface);
		border: 1px solid var(--border);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
		color: var(--text);
		font-size: .7rem;
		line-height: 1.35;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		pointer-events: none;
		opacity: 0;
		visibility: hidden;
		transition: opacity .15s ease, visibility .15s ease;
	}
	:global(.shape-node:hover) .shape-note-popover,
	:global(.shape-node:focus-within) .shape-note-popover,
	.shape-note-popover.force-visible {
		opacity: 1;
		visibility: visible;
	}
</style>
```

---

### 2. Edit `web/src/routes/whiteboard/IconNode.svelte` (Lines 9–46)

Update `IconNode.svelte` so icon nodes also support editable labels and unobtrusive hover/selector notes consistently:

**`oldString`:**
```svelte
	type IconNodeType = Node<{ label?: string; icon?: string }, 'icon'>;

	let { data, selected }: NodeProps<IconNodeType> = $props();

	const map: Record<string, typeof Sparkles> = {
		Sparkles, Type, Notebook, Scissors, Layers, Link,
		Map, Book, Flag, Eye, Clock, Compass, Globe,
		Mountain, Sun, Cloud, Wind, Flame, Droplets,
		Trash2, Plus, Square, Circle, Triangle, ArrowRight
	};

	const icon = $derived(data?.icon || 'Sparkles');
	const label = $derived(data?.label || icon);
	const IconComp = $derived(map[icon] || Sparkles);
</script>

<div class="icon-node {selected ? 'selected' : ''}">
	<Handle type="target" position={Position.Left} />
	<IconComp size={24} style="color:var(--accent)" />
	<span class="icon-label">{label}</span>
	<Handle type="source" position={Position.Right} />
</div>

<style>
	:global(.icon-node) {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
		padding: 10px 16px;
		border-radius: 8px;
		background: var(--surface);
		border: 1.5px solid var(--border);
		cursor: pointer;
		user-select: none;
		min-width: 76px;
	}
```

**`newString`:**
```svelte
	type IconNodeData = {
		label?: string;
		icon?: string;
		note?: string;
		showNotes?: boolean;
		onUpdate?: (patch: { label?: string; note?: string }) => void;
	};
	type IconNodeType = Node<IconNodeData, 'icon'>;

	let { data, selected }: NodeProps<IconNodeType> = $props();

	const map: Record<string, typeof Sparkles> = {
		Sparkles, Type, Notebook, Scissors, Layers, Link,
		Map, Book, Flag, Eye, Clock, Compass, Globe,
		Mountain, Sun, Cloud, Wind, Flame, Droplets,
		Trash2, Plus, Square, Circle, Triangle, ArrowRight
	};

	const icon = $derived(data?.icon || 'Sparkles');
	const label = $derived(data?.label || icon);
	const note = $derived(data?.note || '');
	const showNotes = $derived(Boolean(data?.showNotes));
	const IconComp = $derived(map[icon] || Sparkles);
</script>

<div class="icon-node {selected ? 'selected' : ''}">
	<Handle type="target" position={Position.Left} />
	{#if note}
		<div class="icon-note-popover {showNotes ? 'force-visible' : ''}" role="note">
			{note}
		</div>
	{/if}
	<IconComp size={24} style="color:var(--accent)" />
	<span class="icon-label">{label}</span>
	<Handle type="source" position={Position.Right} />
</div>

<style>
	:global(.icon-node) {
		position: relative;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
		padding: 10px 16px;
		border-radius: 8px;
		background: var(--surface);
		border: 1.5px solid var(--border);
		cursor: pointer;
		user-select: none;
		min-width: 76px;
	}
	.icon-note-popover {
		position: absolute;
		bottom: calc(100% + 6px);
		left: 50%;
		transform: translateX(-50%);
		z-index: 40;
		min-width: 110px;
		max-width: 200px;
		padding: 5px 8px;
		border-radius: 6px;
		background: var(--surface);
		border: 1px solid var(--border);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
		color: var(--text);
		font-size: .7rem;
		line-height: 1.35;
		white-space: pre-wrap;
		pointer-events: none;
		opacity: 0;
		visibility: hidden;
		transition: opacity .15s ease, visibility .15s ease;
	}
	:global(.icon-node:hover) .icon-note-popover,
	:global(.icon-node:focus-within) .icon-note-popover,
	.icon-note-popover.force-visible {
		opacity: 1;
		visibility: visible;
	}
```

---

### 3. Edit `web/src/routes/whiteboard/+page.svelte`

#### Edit 3a: Imports and state declarations (Lines 17–75)

**`oldString`:**
```svelte
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
```

**`newString`:**
```svelte
	import {
		Square, Circle, Triangle, ArrowRight, Minus,
		Type, Sparkles, Scissors, Layers, Link,
		Map, Book, Flag, Eye, Clock, Compass,
		Globe, Mountain, Sun, Cloud, Wind,
		Flame, Droplets, Trash2, Plus,
		Minimize, ZoomIn, ZoomOut, StickyNote
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
	let showAllNotes = $state(false);
	let selectedNodeShape = $state('rectangle');
	let selectedNodeIcon = $state('Sparkles');
	let error = $state('');
	let viewport = $state<Viewport>({ x: 0, y: 0, zoom: 1 });
	let autoSaveTimer: ReturnType<typeof setTimeout> | null = null;

	const selectedNode = $derived(selectedId ? (nodes.find((n) => n.id === selectedId) ?? null) : null);

	function patchNodeData(nodeId: string, patch: { label?: string; note?: string; text?: string }) {
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
				edges = data.edges || [];
				if (data.viewport) viewport = data.viewport;
			}
		} catch {
			error = 'Could not load whiteboard';
		}
	}
```

#### Edit 3b: `addNode` and `toggleShowAllNotes` helper in `web/src/routes/whiteboard/+page.svelte` (Lines 96–119)

**`oldString`:**
```svelte
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
```

**`newString`:**
```svelte
	function addNode(type: string, label: string, shapeOverride?: string) {
		const id = `node_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
		const pos = nextPosition(nodes.length);
		const shape = shapeOverride ?? selectedNodeShape;
		const baseData =
			type === 'icon'
				? { icon: selectedNodeIcon, label, note: '' }
				: type === 'note'
					? { text: label }
					: { shape, label, note: '' };
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
		iconPickerOpen = false;
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
```

#### Edit 3c: Add "Show notes" selector button and selected shape label/note editor in `web/src/routes/whiteboard/+page.svelte` toolbar

Locate the `<!-- Zoom -->` section and `toolbar-hint` in `web/src/routes/whiteboard/+page.svelte`:

**`oldString`:**
```svelte
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
```

**`newString`:**
```svelte
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

			{#if selectedNode && (selectedNode.type === 'shape' || selectedNode.type === 'icon')}
				<div class="node-inspector">
					<input
						type="text"
						class="node-inspector-input"
						aria-label="Shape label"
						placeholder="Shape name"
						value={String(selectedNode.data?.label ?? '')}
						oninput={(e) => patchNodeData(selectedNode.id, { label: e.currentTarget.value })}
					/>
					<input
						type="text"
						class="node-inspector-input"
						aria-label="Shape note"
						placeholder="Add shape note..."
						value={String(selectedNode.data?.note ?? '')}
						oninput={(e) => patchNodeData(selectedNode.id, { note: e.currentTarget.value })}
					/>
				</div>
			{/if}

			{#if connectionMode}
				<div class="toolbar-hint">
					{connectFromId ? 'Click target node to link' : 'Click first node (or drag between handles)'}
				</div>
			{/if}
		</div>
```

#### Edit 3d: Add CSS styles for `.node-inspector` in `web/src/routes/whiteboard/+page.svelte`

Locate `.toolbar-hint` in `<style>` in `web/src/routes/whiteboard/+page.svelte`:

**`oldString`:**
```css
	.toolbar-hint {
		font-size: .75rem;
		padding: .3rem .6rem;
		border-radius: .375rem;
		background: var(--surface);
		border: 1px solid var(--accent);
		color: var(--text);
		box-shadow: 0 2px 8px rgba(0,0,0,.15);
	}
```

**`newString`:**
```css
	.toolbar-hint {
		font-size: .75rem;
		padding: .3rem .6rem;
		border-radius: .375rem;
		background: var(--surface);
		border: 1px solid var(--accent);
		color: var(--text);
		box-shadow: 0 2px 8px rgba(0,0,0,.15);
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
```

---

## Verification & Testing Instructions for Chunk 1

1. Update `web/e2e/project-flow.spec.ts` in the `whiteboard:` test (around line 98) to verify editing a shape's label, adding a note to a shape, and toggling `Show notes`:

**`oldString` in `web/e2e/project-flow.spec.ts`:**
```ts
	// Drop two shapes from the add-node menu onto the canvas.
	await page.getByTitle('Add node').click();
	await page.getByRole('button', { name: 'Shape', exact: true }).click();
	await expect(page.locator('.svelte-flow__node')).toHaveCount(1);
	await expect(page.locator('.svelte-flow__node')).toContainText('Shape');
```

**`newString` in `web/e2e/project-flow.spec.ts`:**
```ts
	// Drop two shapes from the add-node menu onto the canvas.
	await page.getByTitle('Add node').click();
	await page.getByRole('button', { name: 'Shape', exact: true }).click();
	await expect(page.locator('.svelte-flow__node')).toHaveCount(1);
	await expect(page.locator('.svelte-flow__node')).toContainText('Shape');

	// Edit the shape's label and add a note after adding to the board.
	await page.getByLabel('Shape label').fill('Protagonist');
	await page.getByLabel('Shape note').fill('Secretly the heir');
	await expect(page.locator('.svelte-flow__node').first()).toContainText('Protagonist');

	// Toggle "Show notes" selector so the note is visible unobtrusively.
	await page.getByTitle('Show notes').click();
	await expect(page.locator('.shape-note-popover.force-visible')).toContainText('Secretly the heir');
```

2. Run checks, unit tests, build, and Playwright E2E tests:
   ```bash
   cd web && npm run check && npm test && npm run build && npx playwright test e2e/project-flow.spec.ts
   ```
3. **Update Markdown Files & Pause:**
   - Update `README.md`, `web/README.md`, `PLAN.md` (Phase 6c), `features.md`, and `chunk-1-whiteboard-labels-and-notes.md` to mark Chunk 1 as `✅ Complete (Tests Passing)`.
   - **PAUSE HERE** and ask the user for permission to proceed to Chunk 2.
