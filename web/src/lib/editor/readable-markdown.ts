import { RangeSetBuilder, type Extension } from '@codemirror/state';
import {
	Decoration,
	type DecorationSet,
	EditorView,
	ViewPlugin,
	type ViewUpdate
} from '@codemirror/view';

export interface ReadableSpan {
	from: number;
	to: number;
	kind: 'hide' | 'h1' | 'h2' | 'h3' | 'h4' | 'bold' | 'italic' | 'strike' | 'code' | 'quote';
}

/**
 * Compute spans to hide/style on a single line of Markdown text for Readable Mode.
 * Pure function so it can be unit-tested independently of the DOM.
 */
export function computeLineReadableSpans(lineText: string, lineOffset = 0): ReadableSpan[] {
	const spans: ReadableSpan[] = [];
	const masked = lineText.split('');

	const maskRange = (startIdx: number, endIdx: number) => {
		for (let i = startIdx; i < endIdx; i++) {
			masked[i] = ' ';
		}
	};

	// 1. ATX Headings: # Heading 1 .. ###### Heading 6
	const hMatch = /^(\s*#{1,6})(\s+)(.*)$/.exec(lineText);
	if (hMatch) {
		const hashes = hMatch[1];
		const space = hMatch[2];
		const prefixLen = hashes.length + space.length;
		const level = Math.min(hashes.trim().length, 4) as 1 | 2 | 3 | 4;
		spans.push({ from: lineOffset, to: lineOffset + prefixLen, kind: 'hide' });
		maskRange(0, prefixLen);
		if (lineText.length > prefixLen) {
			spans.push({
				from: lineOffset + prefixLen,
				to: lineOffset + lineText.length,
				kind: `h${level}`
			});
		}
	}

	// 2. Blockquote prefix: > quote
	const qMatch = /^(\s*>+\s?)(.*)$/.exec(lineText);
	if (qMatch && !hMatch) {
		const qLen = qMatch[1].length;
		spans.push({ from: lineOffset, to: lineOffset + qLen, kind: 'hide' });
		maskRange(0, qLen);
		if (lineText.length > qLen) {
			spans.push({
				from: lineOffset + qLen,
				to: lineOffset + lineText.length,
				kind: 'quote'
			});
		}
	}

	// 3. Inline code: `code` (mask completely so * inside code is not treated as italic)
	const codeRe = /(`)(?!`)(.+?)\1/g;
	let m: RegExpExecArray | null;
	while ((m = codeRe.exec(lineText)) !== null) {
		const start = lineOffset + m.index;
		const end = start + m[0].length;
		spans.push({ from: start, to: start + 1, kind: 'hide' });
		spans.push({ from: start + 1, to: end - 1, kind: 'code' });
		spans.push({ from: end - 1, to: end, kind: 'hide' });
		maskRange(m.index, m.index + m[0].length);
	}

	// 4. Inline bold+italic: ***text*** or ___text___
	const boldItalicRe = /(\*\*\*|___)(.+?)\1/g;
	while ((m = boldItalicRe.exec(masked.join(''))) !== null) {
		const start = lineOffset + m.index;
		const end = start + m[0].length;
		spans.push({ from: start, to: start + 3, kind: 'hide' });
		spans.push({ from: start + 3, to: end - 3, kind: 'bold' });
		spans.push({ from: start + 3, to: end - 3, kind: 'italic' });
		spans.push({ from: end - 3, to: end, kind: 'hide' });
		maskRange(m.index, m.index + m.index === m.index ? m.index + 3 : 0);
		maskRange(m.index + m[0].length - 3, m.index + m[0].length);
	}

	// 5. Inline bold: **text** or __text__
	const boldRe = /(\*\*|__)(.+?)\1/g;
	while ((m = boldRe.exec(masked.join(''))) !== null) {
		if (!m[2].trim()) continue;
		const start = lineOffset + m.index;
		const end = start + m[0].length;
		spans.push({ from: start, to: start + 2, kind: 'hide' });
		spans.push({ from: start + 2, to: end - 2, kind: 'bold' });
		spans.push({ from: end - 2, to: end, kind: 'hide' });
		maskRange(m.index, m.index + 2);
		maskRange(m.index + m[0].length - 2, m.index + m[0].length);
	}

	// 6. Inline strikethrough: ~~text~~
	const strikeRe = /(~~)(.+?)\1/g;
	while ((m = strikeRe.exec(masked.join(''))) !== null) {
		if (!m[2].trim()) continue;
		const start = lineOffset + m.index;
		const end = start + m[0].length;
		spans.push({ from: start, to: start + 2, kind: 'hide' });
		spans.push({ from: start + 2, to: end - 2, kind: 'strike' });
		spans.push({ from: end - 2, to: end, kind: 'hide' });
		maskRange(m.index, m.index + 2);
		maskRange(m.index + m[0].length - 2, m.index + m[0].length);
	}

	// 7. Inline italic: *text* or _text_
	const italicStarRe = /(?<!\*)\*(?!\*)([^*]+?)\*(?!\*)/g;
	while ((m = italicStarRe.exec(masked.join(''))) !== null) {
		if (!m[1].trim()) continue;
		const start = lineOffset + m.index;
		const end = start + m[0].length;
		spans.push({ from: start, to: start + 1, kind: 'hide' });
		spans.push({ from: start + 1, to: end - 1, kind: 'italic' });
		spans.push({ from: end - 1, to: end, kind: 'hide' });
		maskRange(m.index, m.index + 1);
		maskRange(m.index + m[0].length - 1, m.index + m[0].length);
	}

	const italicUnderRe = /(?<!_)_(?!_)([^_]+?)_(?!_)/g;
	while ((m = italicUnderRe.exec(masked.join(''))) !== null) {
		if (!m[1].trim()) continue;
		const start = lineOffset + m.index;
		const end = start + m[0].length;
		spans.push({ from: start, to: start + 1, kind: 'hide' });
		spans.push({ from: start + 1, to: end - 1, kind: 'italic' });
		spans.push({ from: end - 1, to: end, kind: 'hide' });
	}

	return spans.sort((a, b) => a.from - b.from || a.to - b.to);
}

const hideDeco = Decoration.replace({});
const markDecos: Record<Exclude<ReadableSpan['kind'], 'hide'>, Decoration> = {
	h1: Decoration.mark({ class: 'cm-readable-h1' }),
	h2: Decoration.mark({ class: 'cm-readable-h2' }),
	h3: Decoration.mark({ class: 'cm-readable-h3' }),
	h4: Decoration.mark({ class: 'cm-readable-h4' }),
	bold: Decoration.mark({ class: 'cm-readable-bold' }),
	italic: Decoration.mark({ class: 'cm-readable-italic' }),
	strike: Decoration.mark({ class: 'cm-readable-strike' }),
	code: Decoration.mark({ class: 'cm-readable-code' }),
	quote: Decoration.mark({ class: 'cm-readable-quote' })
};

function buildReadableDecorations(view: EditorView, enabled: boolean): DecorationSet {
	const builder = new RangeSetBuilder<Decoration>();
	if (!enabled) return builder.finish();

	const doc = view.state.doc;
	const sel = view.state.selection.main;
	const hasRangeSelection = sel.from < sel.to;

	const allSpans: ReadableSpan[] = [];
	for (let i = 1; i <= doc.lines; i++) {
		const line = doc.line(i);
		if (!line.text.trim()) continue;
		// Only skip a line if the user is actively dragging a text selection across it
		if (hasRangeSelection && line.from <= sel.to && line.to >= sel.from) {
			continue;
		}
		allSpans.push(...computeLineReadableSpans(line.text, line.from));
	}

	allSpans.sort((a, b) => a.from - b.from || a.to - b.to);
	let lastHideEnd = -1;
	for (const s of allSpans) {
		if (s.from >= s.to) continue;
		if (s.kind === 'hide') {
			if (s.from < lastHideEnd) continue;
			builder.add(s.from, s.to, hideDeco);
			lastHideEnd = s.to;
		} else {
			builder.add(s.from, s.to, markDecos[s.kind]);
		}
	}
	return builder.finish();
}

export function readableMarkdownExtension(getEnabled: () => boolean): Extension {
	return ViewPlugin.fromClass(
		class {
			decorations: DecorationSet;
			lastEnabled: boolean;
			constructor(view: EditorView) {
				this.lastEnabled = getEnabled();
				this.decorations = buildReadableDecorations(view, this.lastEnabled);
			}
			update(update: ViewUpdate) {
				const enabled = getEnabled();
				if (
					enabled !== this.lastEnabled ||
					update.docChanged ||
					update.selectionSet ||
					update.viewportChanged ||
					update.transactions.length > 0
				) {
					this.lastEnabled = enabled;
					this.decorations = buildReadableDecorations(update.view, enabled);
				}
			}
		},
		{
			decorations: (v) => v.decorations
		}
	);
}
