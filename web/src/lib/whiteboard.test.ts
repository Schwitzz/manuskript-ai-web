import { describe, expect, it } from 'vitest';
import type { Edge } from '@xyflow/svelte';
import type { OutlineItem, LabelDef } from './outline.ts';
import { buildNodes, collectIds, filterEdges, mergeLayout, type SavedLayout } from './whiteboard.ts';

const labels: LabelDef[] = [
	{ name: 'Main', color: '#ff0000' },
	{ name: 'Sub', color: '#00ff00' },
];
const statusList = ['Draft', 'Reviewed', 'Final'];

const items: OutlineItem[] = [
	{
		id: 1,
		title: 'Act 1',
		type: 'folder',
		words: 5000,
		status: '',
		label: '',
		pov: '',
		goal: '',
		compile: '',
		summary_sentence: 'The beginning',
		summary_full: '',
		notes: '',
		parent_id: null,
		position: 0,
		children: [
			{
				id: 2,
				title: 'Scene One',
				type: 'md',
				words: 1500,
				status: '2',
				label: '1',
				pov: '1',
				goal: '2000',
				compile: '',
				summary_sentence: 'Hero arrives',
				summary_full: '',
				notes: '',
				parent_id: 1,
				position: 0,
				children: [],
			},
			{
				id: 3,
				title: 'Scene Two',
				type: 'text',
				words: 800,
				status: '1',
				label: '',
				pov: '',
				goal: '',
				compile: '',
				summary_sentence: 'Conflict begins',
				summary_full: '',
				notes: '',
				parent_id: 1,
				position: 1,
				children: [],
			},
			{
				id: 4,
				title: 'Note',
				type: 'note',
				words: 100,
				status: '',
				label: '',
				pov: '',
				goal: '',
				compile: '',
				summary_sentence: 'A note',
				summary_full: '',
				notes: '',
				parent_id: 1,
				position: 2,
				children: [],
			},
		],
	},
];

const edges: Edge[] = [
	{ id: 'e1', source: '2', target: '3', sourceHandle: null, targetHandle: null },
	{ id: 'e2', source: '2', target: '99', sourceHandle: null, targetHandle: null },
	{ id: 'e3', source: '3', target: '1', sourceHandle: null, targetHandle: null },
];

describe('buildNodes', () => {
	it('creates nodes for all items recursively (folders, scenes, notes)', () => {
		const nodes = buildNodes(items, labels, statusList, {});
		expect(nodes.map((n) => n.id)).toEqual(['1', '2', '3', '4']);
	});

	it('populates node data from outline fields', () => {
		const nodes = buildNodes(items, labels, statusList, {});
		const scene = nodes.find((n) => n.id === '2')!;
		expect(scene.data).toMatchObject({
			title: 'Scene One',
			type: 'md',
			summary: 'Hero arrives',
			words: 1500,
			status: 'Reviewed',
			label: '1',
			color: '#ff0000',
		});
	});

	it('applies saved positions when available', () => {
		const savedPos = { '1': { x: 100, y: 200 } };
		const nodes = buildNodes(items, labels, statusList, savedPos);
		expect(nodes.find((n) => n.id === '1')!.position).toEqual({ x: 100, y: 200 });
		// Node 2 has no saved position, gets default
		expect(nodes.find((n) => n.id === '2')!.position.x).toBeGreaterThan(0);
	});

	it('returns empty array for no items', () => {
		expect(buildNodes([], labels, statusList, {})).toEqual([]);
	});
});

describe('collectIds', () => {
	it('collects all IDs from the tree', () => {
		const ids = collectIds(items);
		expect(ids).toEqual(new Set(['1', '2', '3', '4']));
	});
});

describe('filterEdges', () => {
	it('keeps edges where both endpoints exist', () => {
		const ids = new Set(['1', '2', '3', '4']);
		const filtered = filterEdges(edges, ids);
		expect(filtered.map((e) => e.id)).toEqual(['e1', 'e3']);
	});

	it('removes edges with missing endpoints', () => {
		const ids = new Set(['1', '2']);
		const filtered = filterEdges(edges, ids);
		// e1: 2->3 (3 missing), e2: 2->99 (99 missing), e3: 3->1 (3 missing)
		expect(filtered).toEqual([]);
	});
});

describe('mergeLayout', () => {
	it('builds nodes and returns default viewport when no saved layout', () => {
		const { nodes, edges: mergedEdges, viewport } = mergeLayout(items, labels, statusList, null);
		expect(nodes.length).toBe(4);
		expect(mergedEdges).toEqual([]);
		expect(viewport).toEqual({ x: 0, y: 0, zoom: 1 });
	});

	it('preserves saved positions for existing nodes', () => {
		const saved: SavedLayout = {
			version: 1,
			nodes: [
				{ id: '1', position: { x: 100, y: 200 } },
				{ id: '2', position: { x: 300, y: 400 } },
			],
			edges,
			viewport: { x: 10, y: 20, zoom: 1.5 },
		};
		const { nodes, edges: mergedEdges, viewport } = mergeLayout(items, labels, statusList, saved);
		expect(nodes.find((n) => n.id === '1')!.position).toEqual({ x: 100, y: 200 });
		expect(nodes.find((n) => n.id === '2')!.position).toEqual({ x: 300, y: 400 });
		expect(viewport).toEqual({ x: 10, y: 20, zoom: 1.5 });
		// e1 (2->3) kept, e2 (2->99) removed, e3 (3->1) kept
		expect(mergedEdges.map((e) => e.id)).toEqual(['e1', 'e3']);
	});

	it('gives new nodes default positions when not in saved layout', () => {
		const saved: SavedLayout = {
			version: 1,
			nodes: [{ id: '1', position: { x: 50, y: 60 } }],
			edges: [],
			viewport: { x: 0, y: 0, zoom: 1 },
		};
		const { nodes } = mergeLayout(items, labels, statusList, saved);
		expect(nodes.find((n) => n.id === '1')!.position).toEqual({ x: 50, y: 60 });
		// Nodes 2, 3, 4 get default positions (not 0,0)
		expect(nodes.find((n) => n.id === '2')!.position.x).toBeGreaterThan(0);
	});

	it('filters edges to only those with existing endpoints', () => {
		const saved: SavedLayout = {
			version: 1,
			nodes: [],
			edges,
			viewport: { x: 0, y: 0, zoom: 1 },
		};
		const { edges: mergedEdges } = mergeLayout(items, labels, statusList, saved);
		expect(mergedEdges.map((e) => e.id)).toEqual(['e1', 'e3']);
	});
});