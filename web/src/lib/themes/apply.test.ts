import { describe, expect, it } from 'vitest';
import { contrast } from './colors.ts';
import {
DEFAULT_APPEARANCE,
STORAGE_KEY,
apply,
load,
resolveScheme,
sanitize,
save,
type Root
} from './apply.ts';
import { SCHEMES } from './schemes.ts';

function fakeRoot() {
const props: Record<string, string> = {};
const root: Root = {
style: { setProperty: (n, v) => void (props[n] = v) },
dataset: {}
};
return { root, props };
}

function fakeStorage(initial: Record<string, string> = {}) {
const data = { ...initial };
return {
data,
getItem: (k: string) => data[k] ?? null,
setItem: (k: string, v: string) => void (data[k] = v)
};
}

describe('resolveScheme', () => {
it('follows the device for System', () => {
expect(resolveScheme('system', true).dark).toBe(true);
expect(resolveScheme('system', false).dark).toBe(false);
expect(resolveScheme('system', false).id).toBe('paper');
});
it('falls back to the default for unknown ids', () => {
expect(resolveScheme('nope', false).id).toBe('midnight');
});
});

describe('sanitize', () => {
it('keeps valid values', () => {
const a = { scheme: 'nord', accent: '#AABBCC', density: 'compact', fontScale: 1.2 };
expect(sanitize(a)).toEqual({ ...a, accent: '#aabbcc' });
});
it('replaces anything invalid with defaults', () => {
expect(sanitize(null)).toEqual(DEFAULT_APPEARANCE);
expect(sanitize('garbage')).toEqual(DEFAULT_APPEARANCE);
expect(sanitize({ scheme: 'gone', accent: 'red', density: 'huge', fontScale: 'x' })).toEqual(
DEFAULT_APPEARANCE
);
expect(sanitize({ accent: '#12345' }).accent).toBeNull();
expect(sanitize({ scheme: 'system' }).scheme).toBe('system');
});
it('clamps the font scale', () => {
expect(sanitize({ fontScale: 99 }).fontScale).toBe(1.5);
expect(sanitize({ fontScale: 0.01 }).fontScale).toBe(0.85);
expect(sanitize({ fontScale: NaN }).fontScale).toBe(1);
expect(sanitize({ fontScale: Infinity }).fontScale).toBe(1);
});
});

describe('load / save', () => {
it('round-trips through storage', () => {
const st = fakeStorage();
const a = { scheme: 'dracula', accent: '#ff00aa', density: 'spacious' as const, fontScale: 1.1 };
save(st, a);
expect(load(st)).toEqual(a);
});
it('survives missing, corrupt and throwing storage', () => {
expect(load(undefined)).toEqual(DEFAULT_APPEARANCE);
expect(load(fakeStorage())).toEqual(DEFAULT_APPEARANCE);
expect(load(fakeStorage({ [STORAGE_KEY]: '{not json' }))).toEqual(DEFAULT_APPEARANCE);
expect(
load({
getItem: () => {
throw new Error('denied');
}
})
).toEqual(DEFAULT_APPEARANCE);
expect(() =>
save(
{
setItem: () => {
throw new Error('quota');
}
},
DEFAULT_APPEARANCE
)
).not.toThrow();
});
});

describe('apply', () => {
it('sets colours, scale, color-scheme and data attributes', () => {
const { root, props } = fakeRoot();
const s = apply(root, DEFAULT_APPEARANCE, true);
expect(s.id).toBe('midnight');
expect(props['--bg']).toBe(s.window);
expect(props['--editor']).toBe(s.editor);
expect(props['--ui-scale']).toBe('1');
expect(props['color-scheme']).toBe('dark');
expect(root.dataset.theme).toBe('midnight');
expect(root.dataset.density).toBe('comfortable');
});

it('switching theme changes every colour, live', () => {
const { root, props } = fakeRoot();
apply(root, { ...DEFAULT_APPEARANCE, scheme: 'midnight' }, true);
const before = { ...props };
apply(root, { ...DEFAULT_APPEARANCE, scheme: 'paper' }, true);
expect(props['--bg']).not.toBe(before['--bg']);
expect(props['--text']).not.toBe(before['--text']);
expect(props['color-scheme']).toBe('light');
expect(root.dataset.theme).toBe('paper');
});

it('density and font size multiply into one scale', () => {
const { root, props } = fakeRoot();
apply(root, { ...DEFAULT_APPEARANCE, density: 'compact', fontScale: 1 }, true);
expect(Number(props['--ui-scale'])).toBeCloseTo(0.85);
apply(root, { ...DEFAULT_APPEARANCE, density: 'spacious', fontScale: 1.5 }, true);
expect(Number(props['--ui-scale'])).toBeCloseTo(1.8);
});

it('System follows the device and a custom accent is honoured', () => {
const { root, props } = fakeRoot();
apply(root, { ...DEFAULT_APPEARANCE, scheme: 'system' }, false);
expect(root.dataset.theme).toBe('paper');
apply(root, { ...DEFAULT_APPEARANCE, scheme: 'system', accent: '#ff0000' }, true);
expect(root.dataset.theme).toBe('midnight');
expect(props['--accent']).toBe('#ff0000');
});

it.each(SCHEMES.map((s) => [s.id, s] as const))('%s: applied text is readable on every surface', (_i, s) => {
const { root, props } = fakeRoot();
apply(root, { ...DEFAULT_APPEARANCE, scheme: s.id }, true);
for (const surface of ['--bg', '--surface', '--editor']) {
expect(contrast(props['--text'], props[surface])).toBeGreaterThanOrEqual(7);
}
});
});
