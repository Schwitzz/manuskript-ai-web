/**
 * Pure logic for the whiteboard flow view — extracted from Whiteboard.svelte
 * so it can be unit-tested without rendering SvelteFlow.
 */
import type { Edge } from '@xyflow/svelte';
import type { OutlineItem, LabelDef } from './outline.ts';
import { labelColor } from './outline.ts';

export type WhiteboardNode = {
	id: string;
	position: { x: number; y: number };
	data: {
		id: number;
		title: string;
		type: string;
		summary: string;
		words: number;
		label: string;
		color: string;
		status: string;
	};
};

export type SavedLayout = {
	version: number;
	nodes: { id: string; position: { x: number; y: number } }[];
	edges: Edge[];
	viewport: { x: number; y: number; zoom: number };
};

/**
 * Recursively walk the outline tree and build flow nodes for every item.
 * Saved positions are applied where available; new items get grid positions.
 */
export function buildNodes(
	items: OutlineItem[],
	labels: LabelDef[],
	statusList: string[],
	savedPos: Record<string, { x: number; y: number }>,
): WhiteboardNode[] {
	const result: WhiteboardNode[] = [];
	function walk(list: OutlineItem[], depth: number) {
		for (const item of list) {
			const color = item.label ? labelColor(labels, item.label) : '';
			const status = item.status ? (statusList[Number(item.status) - 1] ?? '') : '';
			const key = String(item.id);
			const pos = savedPos[key] ?? { x: 60 + depth * 320, y: result.length * 200 };
			result.push({
				id: key,
				position: pos,
				data: {
					id: item.id,
					title: item.title,
					type: item.type,
					summary: item.summary_sentence || item.summary_full || '',
					words: item.words,
					label: item.label,
					color,
					status,
				},
			});
			if (item.type === 'folder' && item.children) {
				walk(item.children, depth + 1);
			}
		}
	}
	walk(items, 0);
	return result;
}

/** Collect all item IDs from the tree as a Set of string IDs. */
export function collectIds(items: OutlineItem[]): Set<string> {
	const ids = new Set<string>();
	function walk(list: OutlineItem[]) {
		for (const item of list) {
			ids.add(String(item.id));
			if (item.children) walk(item.children);
		}
	}
	walk(items);
	return ids;
}

/** Remove edges whose source or target no longer exist in the node set. */
export function filterEdges(edges: Edge[], nodeIds: Set<string>): Edge[] {
	return edges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target));
}

/**
 * Merge a saved layout with the current outline items.
 * - Saved positions are preserved for nodes that still exist.
 * - New nodes get default positions based on depth and index.
 * - Edges are filtered to only those whose endpoints still exist.
 */
export function mergeLayout(
	items: OutlineItem[],
	labels: LabelDef[],
	statusList: string[],
	saved: SavedLayout | null,
): { nodes: WhiteboardNode[]; edges: Edge[]; viewport: { x: number; y: number; zoom: number } } {
	const savedPos: Record<string, { x: number; y: number }> = {};
	if (saved) {
		for (const n of saved.nodes) {
			savedPos[n.id] = { x: n.position?.x ?? 0, y: n.position?.y ?? 0 };
		}
	}

	const nodes = buildNodes(items, labels, statusList, savedPos);
	const validIds = collectIds(items);
	const edges = saved ? filterEdges(saved.edges, validIds) : [];
	const viewport = saved?.viewport ?? { x: 0, y: 0, zoom: 1 };

	return { nodes, edges, viewport };
}