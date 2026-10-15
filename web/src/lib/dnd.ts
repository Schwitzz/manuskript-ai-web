/**
 * Pure helpers for drag-and-drop reordering (outline tree and table views).
 *
 * SortableJS reports `oldDraggableIndex` / `newDraggableIndex` — the index of
 * the dragged element before and after the drop, counting only draggable
 * elements. `newDraggableIndex` is the item's *final* position among its
 * siblings. The server's move endpoint takes the insertion index *after* the
 * item has been detached from its old parent, so when moving an item down
 * within the same sibling list we subtract one (see `sameParentPosition`).
 */

import { findItem, flattenWithDepth, type OutlineItem } from './outline.ts';

/**
 * The `position` to send to the move endpoint, given an item's old and new
 * (final) index within the *same* sibling list.
 */
export function sameParentPosition(from: number, to: number): number {
	return to - (from < to ? 1 : 0);
}

/**
 * True if `id` is the folder `ancestorId` itself or is nested inside it.
 * Used to refuse dropping a folder into its own subtree.
 */
export function inSubtree(items: readonly OutlineItem[], ancestorId: number, id: number | null): boolean {
	if (id === null) return false;
	if (id === ancestorId) return true;
	const ancestor = findItem(items, ancestorId);
	return ancestor ? inSubtreeList(ancestor.children, id) : false;
}

function inSubtreeList(items: readonly OutlineItem[], id: number): boolean {
	for (const i of items) {
		if (i.id === id) return true;
		if (inSubtreeList(i.children, id)) return true;
	}
	return false;
}

/**
 * A new outline tree with the item moved to `toParent` (null = top level),
 * inserted at `position` among the new parent's children — the same semantics
 * the move endpoint uses (insertion index after detachment).
 */
export function moveItem(
	items: readonly OutlineItem[],
	id: number,
	toParent: number | null,
	position: number
): OutlineItem[] {
	const next = cloneTree(items);
	const item = detach(next, id);
	if (!item) throw new Error(`Unknown outline item ${id}`);
	attach(next, toParent, item, position);
	return next;
}

/**
 * Compute `{ toParent, position }` when a row in the flattened Table view is
 * dragged to `toFlatIndex` (0-based index among all flattened rows).
 */
export function computeFlatTableMove(
	items: readonly OutlineItem[],
	dragId: number,
	toFlatIndex: number
): { toParent: number | null; position: number } | null {
	const dragged = findItem(items, dragId);
	if (!dragged) return null;

	const allRows = flattenWithDepth(items).map((r) => r.item);
	const remaining = allRows.filter((r) => !inSubtree(items, dragId, r.id));
	const clampedIndex = clamp(toFlatIndex, 0, remaining.length);

	if (dragged.type === 'folder') {
		// Reorder folders/chapters among siblings sharing the same parent_id
		const toParent = dragged.parent_id;
		const beforeSlice = remaining.slice(0, clampedIndex);
		const siblingsBefore = beforeSlice.filter((r) => r.parent_id === toParent).length;
		return { toParent, position: siblingsBefore };
	}

	// Dragged item is a scene (leaf item)
	const prevRow = clampedIndex > 0 ? remaining[clampedIndex - 1] : null;
	if (!prevRow) {
		const firstRow = remaining[0];
		return { toParent: firstRow ? firstRow.parent_id : dragged.parent_id, position: 0 };
	}

	if (prevRow.type === 'folder') {
		// Dropped immediately beneath a folder/chapter row -> first child of that folder
		return { toParent: prevRow.id, position: 0 };
	}

	// Dropped beneath another scene -> same parent, right after prevRow
	const toParent = prevRow.parent_id;
	const beforeSlice = remaining.slice(0, clampedIndex);
	const siblingsBefore = beforeSlice.filter((r) => r.parent_id === toParent).length;
	return { toParent, position: siblingsBefore };
}

function cloneTree(items: readonly OutlineItem[]): OutlineItem[] {
	return items.map((i) => ({ ...i, children: cloneTree(i.children) }));
}

function detach(list: OutlineItem[], id: number): OutlineItem | null {
	for (let i = 0; i < list.length; i++) {
		if (list[i].id === id) {
			const [removed] = list.splice(i, 1);
			list.forEach((c, idx) => (c.position = idx));
			return removed;
		}
		const found = detach(list[i].children, id);
		if (found) return found;
	}
	return null;
}

function attach(list: OutlineItem[], parent: number | null, item: OutlineItem, position: number): void {
	let children: OutlineItem[];
	if (parent === null) {
		children = list;
	} else {
		const folder = findItem(list, parent);
		if (!folder) throw new Error(`Unknown folder ${parent}`);
		children = folder.children;
	}
	item.parent_id = parent;
	children.splice(clamp(position, 0, children.length), 0, item);
	children.forEach((c, idx) => (c.position = idx));
}

function clamp(n: number, lo: number, hi: number): number {
	return Math.min(Math.max(n, lo), hi);
}
