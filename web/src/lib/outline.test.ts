import { describe, expect, it } from 'vitest';
import type { OutlineItemOut } from './api-types.ts';
import {
	firstScene,
	flatten,
	flattenWithDepth,
	labelColor,
	nameAt,
	parseAssociatedNotes,
	pathTo,
	resolveParentForAdd,
	toItems
} from './outline.ts';

const tree: OutlineItemOut[] = [
	{
		id: 1,
		title: 'Draft',
		type: 'folder',
		words: 7,
		meta: { compile: '2' },
		children: [
			{ id: 2, title: 'One', type: 'md', words: 7, meta: { label: '3', status: '0', POV: '7', setGoal: '500', summarySentence: 'S' }, children: [] },
			{ id: 3, title: 'Two', type: 'md', words: 0, meta: {}, children: [] }
		]
	}
];

describe('toItems', () => {
	it('maps file keys to fields and tracks parent and position', () => {
		const [draft] = toItems(tree);
		expect(draft.parent_id).toBeNull();
		const [one, two] = draft.children;
		expect([one.parent_id, one.position, two.position]).toEqual([1, 0, 1]);
		expect(one).toMatchObject({ label: '3', pov: '7', goal: '500', summary_sentence: 'S' });
	});

	it('treats "0" and missing as no label/status', () => {
		const [, two] = toItems(tree)[0].children;
		const [one] = toItems(tree)[0].children;
		expect(one.status).toBe('');
		expect(two.label).toBe('');
	});
});

describe('pathTo', () => {
	it('lists the ancestors down to the item, and nothing for an unknown id', () => {
		const items = toItems(tree);
		expect(pathTo(items, 3).map((i) => i.id)).toEqual([1, 3]);
		expect(pathTo(items, 1).map((i) => i.id)).toEqual([1]);
		expect(pathTo(items, 99)).toEqual([]);
	});
});

describe('flatten / firstScene', () => {
	it('walks in reading order and skips folders for the first scene', () => {
		const items = toItems(tree);
		expect(flatten(items).map((i) => i.id)).toEqual([1, 2, 3]);
		expect(firstScene(items)?.id).toBe(2);
	});

	it('returns null when there are no scenes', () => {
		expect(firstScene(toItems([{ id: 1, title: 'F', type: 'folder', words: 0, meta: {}, children: [] }]))).toBeNull();
		expect(firstScene([])).toBeNull();
	});
});

describe('label lookups', () => {
	const labels = [{ name: 'Idea', color: '#ff0' }, { name: 'Note', color: '#0f0' }];
	it('is 1-based and safe out of range', () => {
		expect(nameAt(labels, '2', (l) => l.name)).toBe('Note');
		expect(labelColor(labels, '1')).toBe('#ff0');
		expect(labelColor(labels, '')).toBe('');
		expect(labelColor(labels, '0')).toBe('');
		expect(labelColor(labels, '9')).toBe('');
	});
});

describe('parseAssociatedNotes', () => {
	it('parses valid notes and caps text at 2000 characters', () => {
		const raw = JSON.stringify([{ id: 'n1', title: 'Clue', text: 'x'.repeat(2500) }]);
		const notes = parseAssociatedNotes(raw);
		expect(notes).toHaveLength(1);
		expect(notes[0].title).toBe('Clue');
		expect(notes[0].text).toHaveLength(2000);
	});

	it('returns empty array on missing or invalid JSON', () => {
		expect(parseAssociatedNotes(undefined)).toEqual([]);
		expect(parseAssociatedNotes('not-json')).toEqual([]);
	});
});

describe('resolveParentForAdd & flattenWithDepth (scenes index under chapters)', () => {
	const labels = [
		{ name: 'Idea', color: '#ff0' },
		{ name: 'Note', color: '#0f0' },
		{ name: 'Chapter', color: '#00f' },
		{ name: 'Scene', color: '#f00' }
	];
	const chapterTree: OutlineItemOut[] = [
		{
			id: 10,
			title: 'Chapter 1',
			type: 'folder',
			words: 100,
			meta: { label: '3' },
			children: [
				{ id: 11, title: 'Scene 1', type: 'md', words: 100, meta: { label: '4' }, children: [] }
			]
		}
	];

	it('indexes a new scene under the selected chapter or the selected scene’s parent chapter', () => {
		const items = toItems(chapterTree);
		const ch1 = items[0];
		const sc1 = ch1.children[0];
		expect(resolveParentForAdd(items, labels, 'scene', ch1)).toBe(10);
		expect(resolveParentForAdd(items, labels, 'scene', sc1)).toBe(10);
		expect(resolveParentForAdd(items, labels, 'scene', null)).toBe(10);
	});

	it('places a new chapter as a sibling of an existing chapter rather than inside it', () => {
		const items = toItems(chapterTree);
		const ch1 = items[0];
		const sc1 = ch1.children[0];
		expect(resolveParentForAdd(items, labels, 'chapter', ch1)).toBeNull();
		expect(resolveParentForAdd(items, labels, 'chapter', sc1)).toBeNull();
	});

	it('flattens items with their nesting depth for the table view', () => {
		const items = toItems(chapterTree);
		expect(flattenWithDepth(items).map((r) => ({ id: r.item.id, depth: r.depth }))).toEqual([
			{ id: 10, depth: 0 },
			{ id: 11, depth: 1 }
		]);
	});
});
