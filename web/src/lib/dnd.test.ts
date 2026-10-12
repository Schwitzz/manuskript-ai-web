import { describe, expect, it } from 'vitest';
import { inSubtree, moveItem, reorder, sameParentPosition } from './dnd.ts';
import { toItems, type OutlineItem } from './outline.ts';
import type { OutlineItemOut } from './api-types.ts';

/**
 *  ┌ A ──── B ──── C ──── D
 * Draft(1)   One(2)  Two(3)  Free(4, top level)
 */
const treeOut: OutlineItemOut[] = [
	{
		id: 1,
		title: 'Draft',
		type: 'folder',
		words: 0,
		meta: {},
		children: [
			{ id: 2, title: 'One', type: 'md', words: 0, meta: {}, children: [] },
			{ id: 3, title: 'Two', type: 'md', words: 0, meta: {}, children: [] }
		]
	},
	{ id: 4, title: 'Free', type: 'md', words: 0, meta: {}, children: [] }
];

function tree(): OutlineItem[] {
	return toItems(treeOut);
}

describe('reorder', () => {
	it('moves an element to its final position', () => {
		const list = ['A', 'B', 'C', 'D'];
		expect(reorder(list, 0, 2)).toEqual(['B', 'C', 'A', 'D']);
		expect(reorder(list, 2, 0)).toEqual(['C', 'A', 'B', 'D']);
		expect(reorder(list, 3, 1)).toEqual(['A', 'D', 'B', 'C']);
	});

	it('returns an equivalent array for a no-op move', () => {
		const list = ['A', 'B'];
		expect(reorder(list, 1, 1)).toEqual(['A', 'B']);
	});
});

describe('sameParentPosition', () => {
	it('maps a final index to the server\'s after-detach insertion index', () => {
		// [A B C D]: move A to its final slot 2 -> insert at 1 after detaching A.
		expect(sameParentPosition(0, 2)).toBe(1);
		// move C to slot 0 -> insert at 0.
		expect(sameParentPosition(2, 0)).toBe(0);
		// moving up by one is a plain index.
		expect(sameParentPosition(3, 1)).toBe(1);
		expect(sameParentPosition(0, 0)).toBe(0);
	});
});

describe('inSubtree', () => {
	it('is true for the folder itself and anything nested inside it', () => {
		const items = tree();
		expect(inSubtree(items, 1, 1)).toBe(true);
		expect(inSubtree(items, 1, 2)).toBe(true);
		expect(inSubtree(items, 1, 3)).toBe(true);
		expect(inSubtree(items, 1, 4)).toBe(false);
		expect(inSubtree(items, 1, null)).toBe(false);
		expect(inSubtree(items, 99, 2)).toBe(false);
	});
});

describe('moveItem', () => {
	it('moves within the same parent using after-detach positions', () => {
		const next = moveItem(tree(), 4, null, 1);
		expect(next.map((i) => i.id)).toEqual([1, 4]);
		expect(next[1].children.map((i) => i.id)).toEqual([]);
		// item 1 (Draft) keeps its children intact.
		expect(next[0].children.map((i) => i.id)).toEqual([2, 3]);
	});

	it('moves a scene from the top level into a folder', () => {
		const next = moveItem(tree(), 4, 1, 0);
		expect(next.map((i) => i.id)).toEqual([1]);
		expect(next[0].children.map((i) => i.id)).toEqual([4, 2, 3]);
	});

	it('moves a scene out of a folder to the top level', () => {
		const next = moveItem(tree(), 2, null, 1);
		expect(next.map((i) => i.id)).toEqual([1, 2, 4]); // Free(4) stays at top level
		expect(next[0].children.map((i) => i.id)).toEqual([3]);
	});

	it('reorders inside a folder', () => {
		const next = moveItem(tree(), 3, 1, 0);
		expect(next[0].children.map((i) => i.id)).toEqual([3, 2]);
	});

	it('does not mutate the input tree', () => {
		const before = tree();
		moveItem(before, 2, null, 0);
		expect(before[0].children.map((i) => i.id)).toEqual([2, 3]);
		expect(before.map((i) => i.id)).toEqual([1, 4]);
	});

	it('throws for an unknown item or folder', () => {
		expect(() => moveItem(tree(), 99, null, 0)).toThrow(/Unknown outline item/);
		expect(() => moveItem(tree(), 2, 99, 0)).toThrow(/Unknown folder/);
	});
});
