/** Helpers that turn the API's outline tree (`meta` bag of file keys) into flat, UI-friendly items. */

import type { OutlineItemOut } from './api-types.ts';

export interface AssociatedNote {
	id: string;
	title: string;
	text: string;
}

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
	associated_notes: AssociatedNote[];
	goal: string;
	/** Word count: the scene's own, or the total of everything inside a folder. */
	words: number;
	children: OutlineItem[];
}

export interface LabelDef {
	name: string;
	color: string;
}

export function parseAssociatedNotes(raw: string | undefined): AssociatedNote[] {
	if (!raw) return [];
	try {
		const parsed = JSON.parse(raw);
		if (!Array.isArray(parsed)) return [];
		return parsed
			.filter((n) => n && typeof n.title === 'string')
			.map((n, idx) => ({
				id: typeof n.id === 'string' && n.id ? n.id : `note_${idx}`,
				title: String(n.title),
				text: typeof n.text === 'string' ? n.text.slice(0, 2000) : ''
			}));
	} catch {
		return [];
	}
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
		associated_notes: parseAssociatedNotes(it.meta.associatedNotes),
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

export function isChapterItem(item: OutlineItem, labels: LabelDef[]): boolean {
	const lname = nameAt(labels, item.label, (l) => l.name).toLowerCase();
	if (lname === 'chapter') return true;
	if (lname && lname !== 'chapter') return false;
	return /^chapter\b/i.test(item.title);
}

/**
 * Returns 1 if `siblings[index]` is a non-folder scene that sits beneath a `.md`
 * Chapter in the same sibling list, so scenes visually index under their chapter.
 */
export function siblingDepthOffset(
	siblings: readonly OutlineItem[],
	index: number,
	labels: LabelDef[] = []
): number {
	const item = siblings[index];
	if (!item || item.type === 'folder' || isChapterItem(item, labels)) return 0;
	for (let i = index - 1; i >= 0; i--) {
		if (siblings[i].type === 'folder') return 0;
		if (isChapterItem(siblings[i], labels)) return 1;
	}
	return 0;
}

export function flattenWithDepth(
	items: readonly OutlineItem[],
	depth = 0,
	labels: LabelDef[] = []
): { item: OutlineItem; depth: number }[] {
	return items.flatMap((item, idx) => {
		const itemDepth = depth + siblingDepthOffset(items, idx, labels);
		return [
			{ item, depth: itemDepth },
			...flattenWithDepth(item.children, depth + 1, labels)
		];
	});
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

function siblingsOf(outline: readonly OutlineItem[], parentId: number | null): readonly OutlineItem[] {
	if (parentId === null) return outline;
	return findItem(outline, parentId)?.children ?? [];
}

/**
 * Determine `{ parentId, position }` when adding a 'folder', 'chapter', or 'scene'
 * so that chapters are `.md` items and scenes index directly under their chapter.
 */
export function resolvePlacementForAdd(
	outline: readonly OutlineItem[],
	labels: LabelDef[],
	addingType: 'folder' | 'chapter' | 'scene',
	active: OutlineItem | null
): { parentId: number | null; position: number | null } {
	if (addingType === 'scene') {
		if (active) {
			if (active.type === 'folder') {
				return { parentId: active.id, position: null };
			}
			const siblings = siblingsOf(outline, active.parent_id);
			const idx = siblings.findIndex((s) => s.id === active.id);
			if (idx >= 0) {
				let insertPos = idx + 1;
				while (
					insertPos < siblings.length &&
					siblings[insertPos].type !== 'folder' &&
					!isChapterItem(siblings[insertPos], labels)
				) {
					insertPos++;
				}
				return { parentId: active.parent_id, position: insertPos };
			}
			return { parentId: active.parent_id, position: null };
		}
		const folders = flatten([...outline]).filter((i) => i.type === 'folder');
		return {
			parentId: folders.length > 0 ? folders[folders.length - 1].id : null,
			position: null
		};
	}

	if (addingType === 'chapter') {
		if (!active) {
			const folders = flatten([...outline]).filter((i) => i.type === 'folder');
			return {
				parentId: folders.length > 0 ? folders[0].id : null,
				position: null
			};
		}
		if (active.type === 'folder') {
			if (isChapterItem(active, labels)) return { parentId: active.parent_id, position: null };
			return { parentId: active.id, position: null };
		}
		// Active is an .md chapter or scene: place the new chapter in the same parent folder after the current chapter's scenes
		const siblings = siblingsOf(outline, active.parent_id);
		const idx = siblings.findIndex((s) => s.id === active.id);
		if (idx >= 0) {
			let insertPos = idx + 1;
			while (
				insertPos < siblings.length &&
				siblings[insertPos].type !== 'folder' &&
				!isChapterItem(siblings[insertPos], labels)
			) {
				insertPos++;
			}
			return { parentId: active.parent_id, position: insertPos };
		}
		return { parentId: active.parent_id, position: null };
	}

	// addingType === 'folder'
	if (active?.type === 'folder') return { parentId: active.id, position: null };
	return { parentId: active?.parent_id ?? null, position: null };
}

export function resolveParentForAdd(
	outline: readonly OutlineItem[],
	labels: LabelDef[],
	addingType: 'folder' | 'chapter' | 'scene',
	active: OutlineItem | null
): number | null {
	return resolvePlacementForAdd(outline, labels, addingType, active).parentId;
}
