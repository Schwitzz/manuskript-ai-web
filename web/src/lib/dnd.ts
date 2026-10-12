/**
 * Pure helpers for drag-and-drop reordering (corkboard grid and outline tree).
 *
 * SortableJS reports `oldDraggableIndex` / `newDraggableIndex` — the index of
 * the dragged element before and after the drop, counting only draggable
 * elements. `newDraggableIndex` is the item's *final* position among its
 * siblings. The server's move endpoint takes the insertion index *after* the
 * item has been detached from its old parent, so when moving an item down
 * within the same sibling list we subtract one (see `sameParentPosition`).
 */

import { findItem, type OutlineItem } from './outline.ts';

/** A new array with the element at `from` moved to its final position `to`. */
export function reorder<T>(items: readonly T[], from: number, to: number): T[] {
	const next = [...items];
	const [moved] = next.splice(from, 1);
	next.splice(to, 0, moved);
	return next;
}

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

function cloneTree(items: readonly OutlineItem[]): OutlineItem[] {
	return items.map((i) => ({ ...i, children: cloneTree(i.children) }));
}

function detach(list: OutlineItem[], id: number): OutlineItem | null {
	for (let i = 0; i < list.length; i++) {
		if (list[i].id === id) return list.splice(i, 1)[0];
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
	children.splice(clamp(position, 0, children.length), 0, item);
}

function clamp(n: number, lo: number, hi: number): number {
	return Math.min(Math.max(n, lo), hi);
}
