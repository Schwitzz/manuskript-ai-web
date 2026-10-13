import { describe, expect, it } from 'vitest';
import { sceneFlow, flowTotals, moveInFlow, moveOutOfFolder } from './storyboard.ts';
import type { OutlineItem } from './outline.ts';

const labels = [{ name: 'Main', color: '#ff0000' }];
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
		summary_sentence: '',
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
				status: '1',
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
				type: 'md',
				words: 2000,
				status: '2',
				label: '1',
				pov: '1',
				goal: '2000',
				compile: '',
				summary_sentence: 'Conflict',
				summary_full: '',
				notes: '',
				parent_id: 1,
				position: 1,
				children: [],
			},
		],
	},
	{
		id: 4,
		title: 'Act 2',
		type: 'folder',
		words: 4000,
		status: '',
		label: '',
		pov: '',
		goal: '',
		compile: '',
		summary_sentence: '',
		summary_full: '',
		notes: '',
		parent_id: null,
		position: 1,
		children: [
			{
				id: 5,
				title: 'Scene Three',
				type: 'md',
				words: 3000,
				status: '1',
				label: '2',
				pov: '1',
				goal: '3000',
				compile: '',
				summary_sentence: 'Climax',
				summary_full: '',
				notes: '',
				parent_id: 4,
				position: 0,
				children: [],
			},
		],
	},
];

describe('sceneFlow', () => {
	it('excludes folders and returns scenes in outline order', () => {
		const flow = sceneFlow(items);
		expect(flow.map((i) => i.id)).toEqual([2, 3, 5]);
	});
});

describe('flowTotals', () => {
	it('returns the count of non-folder items', () => {
		expect(flowTotals(items)).toBe(3);
	});
});

describe('moveInFlow', () => {
	it('returns the items list (caller handles API)', () => {
		expect(moveInFlow(items, 2, -1)).toBe(items);
	});

	it('clamps: cannot move first scene earlier within its parent', () => {
		expect(moveInFlow(items, 2, -1)).toBe(items);
	});

	it('returns items unchanged when id not found', () => {
		expect(moveInFlow(items, 999, 1)).toBe(items);
	});
});

describe('moveOutOfFolder', () => {
	it('returns items unchanged when item is not in a folder', () => {
		// Act 2 (id=4) is already top-level
		expect(moveOutOfFolder(items, 4)).toBe(items);
	});
});
