import { describe, expect, it } from 'vitest';
import data from './schemes.json';
import { contrast, ensureContrast, luminance, mix, readableOn, toHex, toRgb } from './colors.ts';
import { DEFAULT_SCHEME, SCHEMES, SYSTEM, cssVariables, derived, getScheme, schemeNames } from './schemes.ts';

describe('colour maths', () => {
it('converts hex both ways, including 3-digit hex', () => {
expect(toRgb('#ff8000')).toEqual([255, 128, 0]);
expect(toRgb('#f80')).toEqual([255, 136, 0]);
expect(toHex([255, 128, 0])).toBe('#ff8000');
expect(toHex([-5, 300, 12.4])).toBe('#00ff0c');
});

it('rounds halves to even like Python', () => {
// Python: round(0.5)=0, round(1.5)=2, round(2.5)=2, round(3.5)=4, round(4.5)=4, round(5.5)=6
		expect(toHex([0.5, 1.5, 2.5])).toBe('#000202');
expect(toHex([3.5, 4.5, 5.5])).toBe('#040406');
});

it('mixes, and gives the extremes of contrast', () => {
expect(mix('#000000', '#ffffff', 0)).toBe('#000000');
expect(mix('#000000', '#ffffff', 1)).toBe('#ffffff');
expect(mix('#000000', '#ffffff', 0.5)).toBe('#808080');
expect(contrast('#000000', '#ffffff')).toBeCloseTo(21, 5);
expect(contrast('#777777', '#777777')).toBeCloseTo(1, 5);
expect(luminance('#ffffff')).toBeCloseTo(1, 5);
});

it('picks readable text and nudges colours to a target ratio', () => {
expect(readableOn('#ffffff')).toBe('#000000');
expect(readableOn('#000000')).toBe('#ffffff');
// Reaches the target when it can...
		const fixed = ensureContrast('#cccccc', '#ffffff', 4.5);
		expect(contrast(fixed, '#ffffff')).toBeGreaterThanOrEqual(4.5);
		// ...is left alone when already fine...
		expect(ensureContrast('#ffffff', '#000000', 4.5)).toBe('#ffffff');
		// ...and, like the desktop, only moves towards white or black, so a mid-grey background
		// can fall short (white on #808080 is 3.95:1). Value taken from the Python original.
		expect(ensureContrast('#777777', '#808080', 4.5)).toBe('#ffffff');
});
});

describe('schemes', () => {
it('has the 31 desktop schemes with unique ids and a default', () => {
expect(SCHEMES).toHaveLength(31);
expect(new Set(SCHEMES.map((s) => s.id)).size).toBe(31);
expect(DEFAULT_SCHEME).toBe('midnight');
expect(getScheme(DEFAULT_SCHEME)?.dark).toBe(true);
expect(SCHEMES.filter((s) => s.dark).length).toBeGreaterThan(SCHEMES.filter((s) => !s.dark).length);
});

it('lists System first and 32 choices in all', () => {
const names = schemeNames();
expect(names[0]).toEqual({ id: SYSTEM, name: 'System' });
expect(names).toHaveLength(32);
expect(getScheme(SYSTEM)).toBeUndefined();
});

it.each(SCHEMES.map((s) => [s.id, s] as const))('%s: WCAG contrast', (_id, s) => {
for (const bg of [s.window, s.panel, s.editor]) {
expect(contrast(s.text, bg)).toBeGreaterThanOrEqual(7);
expect(contrast(s.muted, bg)).toBeGreaterThanOrEqual(4.5);
}
for (const c of [s.accent, s.success, s.warning, s.error]) {
expect(contrast(c, s.editor)).toBeGreaterThanOrEqual(3);
expect(contrast(c, s.panel)).toBeGreaterThanOrEqual(3);
}
const d = derived(s);
expect(contrast(d.selectionText, d.selection)).toBeGreaterThanOrEqual(4.5);
expect(contrast(d.link, s.editor)).toBeGreaterThanOrEqual(4.5);
expect(contrast(d.onAccent, d.accent)).toBeGreaterThanOrEqual(4.5);
});

it('dark flag matches luminance', () => {
for (const s of SCHEMES) expect(luminance(s.window) < 0.2).toBe(s.dark);
});
});

describe('parity with the desktop (Python) implementation', () => {
it.each(data.schemes.map((s) => [s.id, s] as const))('%s: derived colours are identical', (_id, py) => {
const s = getScheme(py.id)!;
expect(derived(s)).toEqual(py.derived);
expect(derived(s, '#ff0000')).toEqual(py.derivedRedAccent);
});
});

describe('cssVariables', () => {
it('emits every variable the app uses, all valid colours', () => {
const vars = cssVariables(getScheme('midnight')!);
expect(Object.keys(vars)).toContain('--bg');
expect(Object.keys(vars)).toContain('--editor');
expect(Object.keys(vars).length).toBeGreaterThanOrEqual(20);
for (const v of Object.values(vars)) expect(v).toMatch(/^#[0-9a-f]{6}$/);
});

it('applies a custom accent consistently', () => {
const vars = cssVariables(getScheme('paper')!, '#ff0000');
expect(vars['--accent']).toBe('#ff0000');
expect(contrast(vars['--link'], vars['--editor'])).toBeGreaterThanOrEqual(4.5);
expect(contrast(vars['--accent-text'], '#ff0000')).toBeGreaterThanOrEqual(4.5);
});
});
