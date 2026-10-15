# Chunk 2: Whiteboard Connector Line Types (Solid, Dash, Dot, Solid Dashed)

**Status:** ✅ Complete (Tests Passing — 135 unit + 18 E2E + 308 server)

## Implementation Notes (Final Architecture)
- **Shared line-type definitions:** `web/src/lib/whiteboard/line-types.ts` defines `LINE_TYPES` (`solid` = `''`, `dash` = `'8 5'`, `dot` = `'2 5'`, `solid-dashed` = `'12 4 2 4'`).
- **Custom SvelteFlow edge (`web/src/routes/whiteboard/DashedEdge.svelte`):** SvelteFlow's default edge did not reliably apply `stroke-dasharray` from inline style strings, so `DashedEdge.svelte` computes the Bezier path via `getBezierPath` and sets `stroke-dasharray={dash || undefined}` and `fill="none"` directly on `<path class="svelte-flow__edge-path">`, plus an invisible 20px `.svelte-flow__edge-interaction` path for easy edge selection.
- **Unified Line Style button & Connection Mode:** Replaced the separate Connection Mode / Arrow-vs-Line / Line Type buttons with a single **Line style** dropdown button in the centered toolbar whose icon renders a live SVG preview of the currently active line style.
- **Drawing lines:** Choosing a line style from the dropdown updates any currently selected edge AND activates `connectionMode = true` (highlighting the button and disabling node drag/canvas pan via `nodesDraggable={!connectionMode}` and `panOnDrag={!connectionMode}` so node clicks are never swallowed by `d3-drag`). Users can connect nodes either by clicking Node 1 → Node 2 or by dragging from Node 1 to Node 2. Clicking the empty canvas exits connection mode.
- **E2E verification:** `web/e2e/project-flow.spec.ts` verifies drawing an edge in connection mode, switching the edge through all four line styles (`Solid dashed`, `Dash`, `Dot`, `Solid`), asserting the rendered `stroke-dasharray` attribute on `.svelte-flow__edge-path` for each style, and confirming persistence across page reload on both phone (`390x844`) and desktop (`1440x900`).

## Scope & Context Budget
- **Files to read/edit:**
  1. `web/src/routes/whiteboard/+page.svelte` (~600 lines)
  2. `web/e2e/project-flow.spec.ts` (~180 lines)
- **Estimated token usage:** ~10k tokens (well under 70k limit).

## What This Chunk Implements
- Adds 4 line types to the Whiteboard for connectors (edges):
  1. `solid`: `stroke: var(--accent); stroke-width: 2px;`
  2. `dash`: `stroke: var(--accent); stroke-width: 2px; stroke-dasharray: 8 5;`
  3. `dot`: `stroke: var(--accent); stroke-width: 2px; stroke-dasharray: 2 5;`
  4. `solid-dashed` (Dash-dot / solid dashed): `stroke: var(--accent); stroke-width: 2px; stroke-dasharray: 12 4 2 4;`
- Adds a **Line type** selector menu in the whiteboard toolbar (`title="Line type"`).
- Selecting a line type updates:
  - `edgeLineType` state for all newly created connections.
  - If an edge is currently selected (`selectedEdgeId`), immediately updates that edge's `style` and `data.lineType` and saves to `localStorage`.
- Selecting an existing edge on the canvas syncs `edgeLineType` to that edge's line type so the user can see and change it.

---

## Step-by-Step Line Edits

### 1. Edit `web/src/routes/whiteboard/+page.svelte`

#### Edit 1a: Add `edgeLineType` state, `LINE_TYPES` definition, and `edgeStyleFor` helper

In `web/src/routes/whiteboard/+page.svelte`, locate `let edgeArrow = $state(true);`:

**`oldString`:**
```svelte
	let edgeArrow = $state(true);
	let showAllNotes = $state(false);
```

**`newString`:**
```svelte
	type LineType = 'solid' | 'dash' | 'dot' | 'solid-dashed';
	const LINE_TYPES: { id: LineType; label: string; dasharray: string }[] = [
		{ id: 'solid', label: 'Solid', dasharray: '' },
		{ id: 'dash', label: 'Dash', dasharray: '8 5' },
		{ id: 'dot', label: 'Dot', dasharray: '2 5' },
		{ id: 'solid-dashed', label: 'Solid dashed', dasharray: '12 4 2 4' }
	];

	let edgeArrow = $state(true);
	let edgeLineType = $state<LineType>('solid');
	let lineTypeMenuOpen = $state(false);
	let showAllNotes = $state(false);

	function edgeStyleFor(lineType: LineType): string {
		const found = LINE_TYPES.find((t) => t.id === lineType);
		const dash = found?.dasharray ? ` stroke-dasharray: ${found.dasharray};` : '';
		return `stroke: var(--accent); stroke-width: 2px;${dash}`;
	}

	function selectLineType(lineType: LineType) {
		edgeLineType = lineType;
		lineTypeMenuOpen = false;
		if (selectedEdgeId) {
			edges = edges.map((e) =>
				e.id === selectedEdgeId
					? { ...e, style: edgeStyleFor(lineType), data: { ...e.data, lineType } }
					: e
			);
			save();
		}
	}
```

#### Edit 1b: Update `buildEdge`, `handleEdgeClick`, and `handlePaneClick` in `web/src/routes/whiteboard/+page.svelte`

**`oldString`:**
```svelte
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
```

**`newString`:**
```svelte
	function buildEdge(source: string, target: string, sourceHandle?: string | null, targetHandle?: string | null): Edge {
		return {
			id: `edge_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
			source,
			target,
			sourceHandle: sourceHandle ?? null,
			targetHandle: targetHandle ?? null,
			type: 'default',
			data: { lineType: edgeLineType },
			style: edgeStyleFor(edgeLineType),
			markerEnd: edgeArrow ? { type: MarkerType.ArrowClosed, color: 'var(--accent)' } : undefined
		};
	}
```

And in `handleEdgeClick` / `handlePaneClick`:

**`oldString`:**
```svelte
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
```

**`newString`:**
```svelte
	function handleEdgeClick({ edge }: { edge: Edge; event: MouseEvent }) {
		selectedEdgeId = edge.id;
		selectedId = null;
		const lt = edge.data?.lineType as LineType | undefined;
		if (lt && LINE_TYPES.some((t) => t.id === lt)) {
			edgeLineType = lt;
		}
	}

	function handlePaneClick() {
		selectedId = null;
		selectedEdgeId = null;
		connectFromId = null;
		toolbarOpen = false;
		toolbarMenuOpen = false;
		iconPickerOpen = false;
		lineTypeMenuOpen = false;
	}
```

#### Edit 1c: Add the Line Type menu button in the Whiteboard toolbar & update `defaultEdgeOptions`

In `web/src/routes/whiteboard/+page.svelte`, locate the `<!-- Connector style: Arrow vs Line -->` button:

**`oldString`:**
```svelte
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
```

**`newString`:**
```svelte
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

				<!-- Line type selector: Solid, Dash, Dot, Solid dashed -->
				<div class="relative">
					<button
						type="button"
						class="toolbar-btn"
						title="Line type"
						aria-label="Line type"
						onclick={() => (lineTypeMenuOpen = !lineTypeMenuOpen)}
					>
						<svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
							<line
								x1="2"
								y1="9"
								x2="16"
								y2="9"
								stroke="currentColor"
								stroke-width="2"
								stroke-dasharray={edgeLineType === 'dash'
									? '4 3'
									: edgeLineType === 'dot'
										? '1.5 3'
										: edgeLineType === 'solid-dashed'
											? '6 2 1.5 2'
											: undefined}
							/>
						</svg>
					</button>
					{#if lineTypeMenuOpen}
						<div class="toolbar-menu">
							<div class="toolbar-menu-title">Line type</div>
							{#each LINE_TYPES as lt (lt.id)}
								<button
									type="button"
									class="toolbar-menu-item {edgeLineType === lt.id ? 'active-item' : ''}"
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
```

Also update `defaultEdgeOptions` on `<SvelteFlow>` in `web/src/routes/whiteboard/+page.svelte`:

**`oldString`:**
```svelte
				defaultEdgeOptions={{
					type: 'default',
					style: 'stroke: var(--accent); stroke-width: 2px;',
					markerEnd: edgeArrow ? { type: MarkerType.ArrowClosed, color: 'var(--accent)' } : undefined
				}}
```

**`newString`:**
```svelte
				defaultEdgeOptions={{
					type: 'default',
					style: edgeStyleFor(edgeLineType),
					markerEnd: edgeArrow ? { type: MarkerType.ArrowClosed, color: 'var(--accent)' } : undefined
				}}
```

---

## Verification & Testing Instructions for Chunk 2

1. Update `web/e2e/project-flow.spec.ts` in the `whiteboard:` test to select a line type (`Solid dashed`) before linking nodes and assert the edge style contains `stroke-dasharray`:

**`oldString` in `web/e2e/project-flow.spec.ts`:**
```ts
	// Link the two nodes using Connection mode.
	await page.getByTitle('Connection mode').click();
	await page.locator('.svelte-flow__node').nth(0).click();
	await page.locator('.svelte-flow__node').nth(1).click();
	await expect(page.locator('.svelte-flow__edge')).toHaveCount(1);
```

**`newString` in `web/e2e/project-flow.spec.ts`:**
```ts
	// Choose a line type (Solid dashed) and link the two nodes using Connection mode.
	await page.getByTitle('Line type').click();
	await expect(page.getByRole('button', { name: 'Solid', exact: true })).toBeVisible();
	await expect(page.getByRole('button', { name: 'Dash', exact: true })).toBeVisible();
	await expect(page.getByRole('button', { name: 'Dot', exact: true })).toBeVisible();
	await page.getByRole('button', { name: 'Solid dashed', exact: true }).click();

	await page.getByTitle('Connection mode').click();
	await page.locator('.svelte-flow__node').nth(0).click();
	await page.locator('.svelte-flow__node').nth(1).click();
	await expect(page.locator('.svelte-flow__edge')).toHaveCount(1);
	await expect(page.locator('.svelte-flow__edge-path').first()).toHaveAttribute('style', /stroke-dasharray:\s*12 4 2 4/);
```

2. Run checks, unit tests, build, and Playwright E2E tests:
   ```bash
   cd web && npm run check && npm test && npm run build && npx playwright test e2e/project-flow.spec.ts
   ```
3. **Update Markdown Files & Pause:**
   - Update `README.md`, `web/README.md`, `PLAN.md` (Phase 6c), `features.md`, and `chunk-2-whiteboard-line-types.md` to mark Chunk 2 as `✅ Complete (Tests Passing)`.
   - **PAUSE HERE** and ask the user for permission to proceed to Chunk 3.
