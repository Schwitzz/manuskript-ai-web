# Upcoming Features Plan (`features.md`)

## Instructions to the Build Agent (READ FIRST)

Before editing any source code, follow this protocol strictly:

1. **Context Preservation:**
   - Work on **one chunk at a time** by reading only that chunk's `.md` file (`chunk-1-whiteboard-labels-and-notes.md`, `chunk-2-whiteboard-line-types.md`, `chunk-3-outline-table-notes-and-chapter-notes.md`, or `chunk-4-scenes-index-under-chapters.md`) and the specific source files listed in that chunk.
2. **Execution & Pause Protocol (CRITICAL):**
   - Apply the exact line-for-line edits specified in the active chunk file.
   - Run the chunk's verification test suite (`vitest`, `svelte-check`, `pytest`, and/or `playwright`).
   - Once tests pass, **update `README.md`, `web/README.md`, `PLAN.md`, `features.md`, and the current `chunk-N-*.md` file** to mark the chunk's status as `✅ Complete (Tests Passing)`.
   - **STOP AND PAUSE** immediately after updating the `.md` files at the passing test stage of each chunk. Report test results to the user and **ask for permission to proceed** to the next chunk. Do **not** start the next chunk until permission is granted.

## Status Tracker
- [x] **Setup**: Created `features.md` and `chunk-1` through `chunk-4` `.md` files.
- [x] **Chunk 1**: Whiteboard editable shape labels & unobtrusive hover/toggle notes (`chunk-1-whiteboard-labels-and-notes.md`) — ✅ Complete (Tests Passing)
- [x] **Chunk 2**: Whiteboard connector line types: solid, dash, dot, solid dashed (`chunk-2-whiteboard-line-types.md`) — ✅ Complete (Tests Passing)
- [x] **Chunk 3**: Outline table/stacked view note field removal & notes on both chapters and scenes (`chunk-3-outline-table-notes-and-chapter-notes.md`) — ✅ Complete (Tests Passing)
- [x] **Chunk 4**: Scenes index (nest) under chapters, not inline (`chunk-4-scenes-index-under-chapters.md`) — ✅ Complete (Tests Passing)

## Feature Overview & Implementation Notes
1. **Whiteboard Editable Shape Labels (✅ Complete)**:
   - Shapes on the whiteboard start with a **blank label** (`''`) by default instead of auto-labeling `"Shape"`, and the first add-menu entry is labeled **Rectangle**.
   - `IconNode.svelte` and the icon node type were removed entirely to keep the board clean.
   - Labels can be edited after adding a shape via the toolbar inspector input when selected or by double-clicking the label on the node.
2. **Whiteboard Shape Notes — Hover + Show Notes Selector (✅ Complete)**:
   - Shapes can have notes attached via the toolbar inspector input.
   - Notes appear unobtrusively on hover (`:hover` / `:focus-within` popover) with a subtle badge indicator, OR all shape notes can be toggled visible simultaneously via the **"Show notes"** button in the centered whiteboard toolbar (ensuring full phone/touch support).
3. **Whiteboard Line Types & Connection Tool (✅ Complete)**:
   - Whiteboard connectors support four line styles—`solid`, `dash` (`8 5`), `dot` (`2 5`), and `solid-dashed` (`12 4 2 4`)—defined in `web/src/lib/whiteboard/line-types.ts` and rendered via a custom SvelteFlow edge component (`web/src/routes/whiteboard/DashedEdge.svelte`) that applies `stroke-dasharray` directly on the SVG `<path class="svelte-flow__edge-path">`.
   - The toolbar is horizontally centered at the top of the board (`left: 50%; transform: translateX(-50%)`).
   - The single **Line style** toolbar button displays a live SVG preview of the currently selected line style. Selecting a line style from its dropdown both updates any currently selected edge and activates `connectionMode` (`nodesDraggable={!connectionMode}`, `panOnDrag={!connectionMode}`), allowing the user to draw lines by clicking Node 1 → Node 2 or dragging from Node 1 to Node 2. Clicking the empty canvas exits connection mode.
4. **Outline Stacked/Table View Note Removal & Chapter/Scene Notes (✅ Complete — Chunk 3)**:
   - Removed the inline `notes` column from the Outline table/stacked view (`COLUMNS`, `EditField`, `cellText`, and table row cell) and removed the standalone `Notes` textarea from the bottom detail panel.
   - Notes are added by highlighting (selecting) any chapter or scene and clicking **Add note** (in the `+` toolbar menu or **+ New note** in the detail panel). Both chapters (`folder` or `md` with Chapter label) and scenes (`md`) support associated notes and detail-panel note management.
5. **Scenes Index Under Chapters, Not Inline (✅ Complete — Chunk 4)**:
   - Creating a Chapter creates a `folder` item (labeled `Chapter`) so scenes can be indexed underneath it.
   - `resolveParentForAdd(outline, labels, addingType, active)` in `web/src/lib/outline.ts` ensures that creating a Scene while a Chapter is selected (or while another Scene inside a Chapter is selected) nests the new Scene inside that Chapter rather than placing it inline at the same level, while creating a new Chapter places it as a sibling of an existing Chapter rather than inside it.
   - In the table view, `flattenWithDepth` renders child scenes indented under their parent chapter in tree order (`padding-left: ${8 + depth * 20}px`).
