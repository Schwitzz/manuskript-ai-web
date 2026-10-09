// Applies a theme to the page as CSS variables. No framework code here, so the same logic can
// run in the pre-paint boot script, in the store, and in tests.

import { DEFAULT_SCHEME, SYSTEM, cssVariables, getScheme, type Scheme } from './schemes.ts';

export const STORAGE_KEY = 'msk.appearance';

export interface Appearance {
	scheme: string; // a scheme id, or "system"
	accent: string | null; // custom accent colour, or null for the scheme's own
	density: 'compact' | 'comfortable' | 'spacious';
	fontScale: number; // 0.85 .. 1.5, interface text size
}

export const DEFAULT_APPEARANCE: Appearance = {
	scheme: DEFAULT_SCHEME,
	accent: null,
	density: 'comfortable',
	fontScale: 1
};

const DENSITY_SCALE = { compact: 0.85, comfortable: 1, spacious: 1.2 } as const;
const HEX = /^#[0-9a-fA-F]{6}$/;

/** System follows the device: dark -> the default dark scheme, light -> Paper. */
export function resolveScheme(id: string, prefersDark: boolean): Scheme {
	const wanted = id === SYSTEM ? (prefersDark ? DEFAULT_SCHEME : 'paper') : id;
	return getScheme(wanted) ?? getScheme(DEFAULT_SCHEME)!;
}

/** Keep only valid values, so a corrupt or old saved value can never break the page. */
export function sanitize(raw: unknown): Appearance {
	const r = (raw && typeof raw === 'object' ? raw : {}) as Record<string, unknown>;
	const scheme =
		typeof r.scheme === 'string' && (r.scheme === SYSTEM || getScheme(r.scheme))
			? r.scheme
			: DEFAULT_APPEARANCE.scheme;
	const accent = typeof r.accent === 'string' && HEX.test(r.accent) ? r.accent.toLowerCase() : null;
	const density =
		r.density === 'compact' || r.density === 'comfortable' || r.density === 'spacious'
			? r.density
			: DEFAULT_APPEARANCE.density;
	const fs = typeof r.fontScale === 'number' && Number.isFinite(r.fontScale) ? r.fontScale : 1;
	return { scheme, accent, density, fontScale: Math.min(1.5, Math.max(0.85, fs)) };
}

export function load(storage: Pick<Storage, 'getItem'> | undefined): Appearance {
	try {
		const text = storage?.getItem(STORAGE_KEY);
		return sanitize(text ? JSON.parse(text) : null);
	} catch {
		return { ...DEFAULT_APPEARANCE };
	}
}

export function save(storage: Pick<Storage, 'setItem'> | undefined, a: Appearance): void {
	try {
		storage?.setItem(STORAGE_KEY, JSON.stringify(a));
	} catch {
		/* private mode or full: the theme still applies for this session */
	}
}

export interface Root {
	style: { setProperty(name: string, value: string): void };
	dataset: Record<string, string | undefined>;
}

/** Write the theme onto <html>. Returns the scheme that was applied. */
export function apply(root: Root, a: Appearance, prefersDark: boolean): Scheme {
	const scheme = resolveScheme(a.scheme, prefersDark);
	for (const [name, value] of Object.entries(cssVariables(scheme, a.accent ?? undefined))) {
		root.style.setProperty(name, value);
	}
	root.style.setProperty('--ui-scale', String(a.fontScale * DENSITY_SCALE[a.density]));
	root.style.setProperty('color-scheme', scheme.dark ? 'dark' : 'light');
	root.dataset.theme = scheme.id;
	root.dataset.density = a.density;
	return scheme;
}
