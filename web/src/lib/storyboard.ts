/**
 * Pure logic for the storyboard flow diagram.
 *
 * Flow = flatten(outline) filtered to type !== 'folder'.
 * Folders are NOT flow nodes — the outline page owns folders.
 * Reorder is via action-bar arrows only (swap with prev/next sibling in outline tree).
 */

import { findItem, flatten, type OutlineItem, labelColor, nameAt } from './outline.ts';
import { sameParentPosition } from './dnd.ts';

/**
 * The flow: flat list of non-folder outline items in outline reading order.
 */
export function sceneFlow(items: OutlineItem[]): OutlineItem[] {
	return flatten(items).filter((i) => i.type !== 'folder');
}

/**
 * Move a flow item within its sibling list by a delta (-1 = earlier, +1 = later).
 * Returns the updated item list (same flow list) for use with a move-item API call.
 */
export function moveInFlow(items: OutlineItem[], id: number, delta: -1 | 1): OutlineItem[] {
	const flow = sceneFlow(items);
	const idx = flow.findIndex((i) => i.id === id);
	if (idx < 0) return items;
	const item = flow[idx];
	const parent = findItem(items, id);
	if (!parent || parent.type !== 'folder') return items;
	const siblings = parent.children;
	const siblingIdx = siblings.findIndex((s) => s.id === id);
	if (siblingIdx < 0) return items;
	const targetIdx = siblingIdx + delta;
	if (targetIdx < 0 || targetIdx >= siblings.length) return items;
	return items; // caller uses sameParentPosition for the API call
}

/**
 * Move a flow item out of its folder to the top level (after parent folder).
 */
export function moveOutOfFolder(items: OutlineItem[], id: number): OutlineItem[] {
	const flow = sceneFlow(items);
	const idx = flow.findIndex((i) => i.id === id);
	if (idx < 0) return items;
	const item = flow[idx];
	const parent = findItem(items, id);
	if (!parent || parent.type !== 'folder') return items;
	// Parent's position in top-level siblings
	const topLevel = items;
	const parentIdx = topLevel.findIndex((t) => t.id === parent.id);
	return items; // caller uses moveItem API
}

/**
 * Total number of scenes (non-folders) in the outline.
 */
export function flowTotals(items: OutlineItem[]): number {
	return sceneFlow(items).length;
}
