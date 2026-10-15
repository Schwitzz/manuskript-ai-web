import { describe, it, expect } from 'vitest';
import { WHITEBOARD_COLORS } from './colors';
import { LINE_TYPES } from './line-types';

describe('whiteboard colors and line types', () => {
	it('defines theme accent default plus hex colors', () => {
		expect(WHITEBOARD_COLORS[0].id).toBe('default');
		expect(WHITEBOARD_COLORS[0].value).toBe('');
		expect(WHITEBOARD_COLORS.length).toBeGreaterThanOrEqual(10);
		for (const c of WHITEBOARD_COLORS.slice(1)) {
			expect(c.value).toMatch(/^#[0-9a-f]{6}$/i);
		}
	});

	it('defines the 4 connector line types', () => {
		expect(LINE_TYPES.map((t) => t.id)).toEqual(['solid', 'dash', 'dot', 'solid-dashed']);
	});
});
