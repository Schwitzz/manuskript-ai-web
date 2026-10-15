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

	// 1. ATX Headings: # Heading 1 .. #### Heading 4
	const hMatch = /^(#{1,6})(\s+)(.*)$/.exec(lineText);
	if (hMatch) {
		const hashes = hMatch[1];
		const space = hMatch[2];
		const prefixLen = hashes.length + space.length;
		const level = Math.min(hashes.length, 4) as 1 | 2 | 3 | 4;
		spans.push({ from: lineOffset, to: lineOffset + prefixLen, kind: 'hide' });
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
		if (lineText.length > qLen) {
			spans.push({
				from: lineOffset + qLen,
				to: lineOffset + lineText.length,
				kind: 'quote'
			});
		}
	}

	// 3. Inline bold: **text** or __text__
	const boldRe = /(\*\*|__)(?=\S)(.+?[*_]*)(?<=\S)\1/g;
	let m: RegExpExecArray | null;
	while ((m = boldRe.exec(lineText)) !== null) {
		const start = lineOffset + m.index;
		const end = start + m[0].length;
		spans.push({ from: start, to: start + 2, kind: 'hide' });
		spans.push({ from: start + 2, to: end - 2, kind: 'bold' });
		spans.push({ from: end - 2, to: end, kind: 'hide' });
	}

	// 4. Inline strikethrough: ~~text~~
	const strikeRe = /(~~)(?=\S)(.+?)(?<=\S)\1/g;
	while ((m = strikeRe.exec(lineText)) !== null) {
		const start = lineOffset + m.index;
		const end = start + m[0].length;
		spans.push({ from: start, to: start + 2, kind: 'hide' });
		spans.push({ from: start + 2, to: end - 2, kind: 'strike' });
		spans.push({ from: end - 2, to: end, kind: 'hide' });
	}

	// 5. Inline italic: *text* (not **)
	const italicRe = /(?<!\*)\*(?!\*)(?=\S)([^*\n]+?)(?<=\S)\*(?!\*)/g;
	while ((m = italicRe.exec(lineText)) !== null) {
		const start = lineOffset + m.index;
		const end = start + m[0].length;
		spans.push({ from: start, to: start + 1, kind: 'hide' });
		spans.push({ from: start + 1, to: end - 1, kind: 'italic' });
		spans.push({ from: end - 1, to: end, kind: 'hide' });
	}

	// 6. Inline code: `code`
	const codeRe = /(`)(?!`)(.+?)\1/g;
	while ((m = codeRe.exec(lineText)) !== null) {
		const start = lineOffset + m.index;
		const end = start + m[0].length;
		spans.push({ from: start, to: start + 1, kind: 'hide' });
		spans.push({ from: start + 1, to: end - 1, kind: 'code' });
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
	const activeStartLine = doc.lineAt(sel.from).number;
	const activeEndLine = doc.lineAt(sel.to).number;

	const allSpans: ReadableSpan[] = [];
	for (let i = 1; i <= doc.lines; i++) {
		if (i >= activeStartLine && i <= activeEndLine) {
			continue; // Active cursor line shows raw Markdown code for seamless editing
		}
		const line = doc.line(i);
		if (!line.text.trim()) continue;
		allSpans.push(...computeLineReadableSpans(line.text, line.from));
	}

	allSpans.sort((a, b) => a.from - b.from || a.to - b.to);
	for (const s of allSpans) {
		if (s.from >= s.to) continue;
		if (s.kind === 'hide') {
			builder.add(s.from, s.to, hideDeco);
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
			constructor(view: EditorView) {
				this.decorations = buildReadableDecorations(view, getEnabled());
			}
			update(update: ViewUpdate) {
				if (update.docChanged || update.selectionSet || update.viewportChanged) {
					this.decorations = buildReadableDecorations(update.view, getEnabled());
				}
			}
		},
		{
			decorations: (v) => v.decorations
		}
	);
}
