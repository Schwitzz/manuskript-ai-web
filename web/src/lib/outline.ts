/** Helpers that turn the API's outline tree (`meta` bag of file keys) into flat, UI-friendly items. */

import type { OutlineItemOut } from './api-types.ts';

export interface OutlineItem {
	id: number;
	title: string;
	type: string;
	parent_id: number | null;
	position: number;
	/** 1-based position in labels.txt, as a string; '' = none (same as desktop Manuskript). */
	label: string;
	/** 1-based position in status.txt, as a string; '' = none. */
	status: string;
	compile: string;
	pov: string;
	summary_sentence: string;
	summary_full: string;
	notes: string;
	goal: string;
	/** Word count: the scene's own, or the total of everything inside a folder. */
	words: number;
	children: OutlineItem[];
}

export interface LabelDef {
	name: string;
	color: string;
}

export function toItems(items: OutlineItemOut[], parentId: number | null = null): OutlineItem[] {
	return items.map((it, position) => ({
		id: it.id,
		title: it.title,
		type: it.type,
		parent_id: parentId,
		position,
		label: labelIndex(it.meta.label),
		status: labelIndex(it.meta.status),
		compile: it.meta.compile ?? '',
		pov: it.meta.POV ?? '',
		summary_sentence: it.meta.summarySentence ?? '',
		summary_full: it.meta.summaryFull ?? '',
		notes: it.meta.notes ?? '',
		goal: it.meta.setGoal ?? '',
		words: it.words,
		children: toItems(it.children, it.id)
	}));
}

/** "0" and "" both mean "none" in the files; normalise so the UI has one empty value. */
function labelIndex(v: string | undefined): string {
	return v && v !== '0' ? v : '';
}

export function findItem(items: readonly OutlineItem[], id: number): OutlineItem | null {
	for (const i of items) {
		if (i.id === id) return i;
		const found = findItem(i.children, id);
		if (found) return found;
	}
	return null;
}

/** Folders from the top down to (and including) the item with this id; [] if it is not found. */
export function pathTo(items: readonly OutlineItem[], id: number): OutlineItem[] {
	for (const i of items) {
		if (i.id === id) return [i];
		const below = pathTo(i.children, id);
		if (below.length) return [i, ...below];
	}
	return [];
}

export function flatten(items: OutlineItem[]): OutlineItem[] {
	return items.flatMap((i) => [i, ...flatten(i.children)]);
}

/** The first scene (not folder) in reading order, or null for a project with no scenes. */
export function firstScene(items: OutlineItem[]): OutlineItem | null {
	return flatten(items).find((i) => i.type !== 'folder') ?? null;
}

/** Name of the label/status at a 1-based position, or '' when none or out of range. */
export function nameAt<T>(list: T[], index: string, pick: (t: T) => string): string {
	const n = Number(index);
	return n >= 1 && n <= list.length ? pick(list[n - 1]) : '';
}

export function labelColor(labels: LabelDef[], index: string): string {
	return nameAt(labels, index, (l) => l.color);
}
