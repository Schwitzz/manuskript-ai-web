import { describe, it, expect } from 'vitest';
import { computeLineReadableSpans } from './readable-markdown';

describe('readable-markdown spans', () => {
	it('hides ATX heading markers and styles heading text', () => {
		const spans = computeLineReadableSpans('## Chapter Two', 10);
		expect(spans).toEqual([
			{ from: 10, to: 13, kind: 'hide' },
			{ from: 13, to: 24, kind: 'h2' }
		]);
	});

	it('hides bold, italic, and strikethrough markers while styling the inner text', () => {
		const spans = computeLineReadableSpans('A **bold** and *italic* and ~~struck~~ word.', 0);
		expect(spans).toContainEqual({ from: 2, to: 4, kind: 'hide' });
		expect(spans).toContainEqual({ from: 4, to: 8, kind: 'bold' });
		expect(spans).toContainEqual({ from: 8, to: 10, kind: 'hide' });
		expect(spans).toContainEqual({ from: 15, to: 16, kind: 'hide' });
		expect(spans).toContainEqual({ from: 16, to: 22, kind: 'italic' });
		expect(spans).toContainEqual({ from: 22, to: 23, kind: 'hide' });
		expect(spans).toContainEqual({ from: 28, to: 30, kind: 'hide' });
		expect(spans).toContainEqual({ from: 30, to: 36, kind: 'strike' });
		expect(spans).toContainEqual({ from: 36, to: 38, kind: 'hide' });
	});

	it('hides blockquote > prefix and styles quote body', () => {
		const spans = computeLineReadableSpans('> Spoken from the shadows', 0);
		expect(spans).toEqual([
			{ from: 0, to: 2, kind: 'hide' },
			{ from: 2, to: 25, kind: 'quote' }
		]);
	});
});
