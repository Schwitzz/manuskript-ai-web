// The 31 desktop colour schemes plus "system". Base colours are the desktop's contrast-adjusted
// values (exported by server/tools/export_schemes.py); derived colours are computed here and
// tested against the desktop's own derived() output.

import data from './schemes.json';
import { contrast, ensureContrast, mix, readableOn } from './colors.ts';

export const SYSTEM = 'system';
export const DEFAULT_SCHEME = data.default as string;

export interface Scheme {
	id: string;
	name: string;
	dark: boolean;
	window: string;
	panel: string;
	editor: string;
	text: string;
	muted: string;
	accent: string;
	success: string;
	warning: string;
	error: string;
}

export interface Derived {
	border: string;
	borderStrong: string;
	hover: string;
	pressed: string;
	selection: string;
	selectionText: string;
	accent: string;
	onAccent: string;
	disabled: string;
	scroll: string;
	scrollHover: string;
	link: string;
	card: string;
	cardBorder: string;
	corkBackground: string;
}

export const SCHEMES: Scheme[] = data.schemes.map(
	({ derived: _d, derivedRedAccent: _r, ...base }) => base as Scheme
);

export function getScheme(id: string): Scheme | undefined {
	return SCHEMES.find((s) => s.id === id);
}

/** Display names with System first. */
export function schemeNames(): { id: string; name: string }[] {
	return [{ id: SYSTEM, name: 'System' }, ...SCHEMES.map((s) => ({ id: s.id, name: s.name }))];
}

/** Colours computed from a scheme; `accent` overrides the scheme's own accent. */
export function derived(s: Scheme, accent?: string): Derived {
	const acc = accent ?? s.accent;
	const selection = mix(s.editor, acc, 0.38);
	return {
		border: mix(s.window, s.text, 0.18),
		borderStrong: mix(s.window, s.text, 0.32),
		hover: mix(s.panel, acc, 0.22),
		pressed: mix(s.panel, acc, 0.34),
		selection,
		selectionText: ensureContrast(s.text, selection, 4.5),
		accent: acc,
		onAccent: readableOn(acc),
		disabled: mix(s.window, s.muted, 0.55),
		scroll: mix(s.window, s.text, 0.22),
		scrollHover: mix(s.window, s.text, 0.38),
		link: ensureContrast(acc, s.editor, 4.5),
		card: mix(s.panel, s.text, 0.05),
		cardBorder: mix(s.panel, s.text, 0.2),
		corkBackground: mix(s.window, s.editor, 0.5)
	};
}

/** Every colour the app uses, as CSS custom properties. */
export function cssVariables(s: Scheme, accent?: string): Record<string, string> {
	const d = derived(s, accent);
	return {
		'--bg': s.window,
		'--surface': s.panel,
		'--editor': s.editor,
		'--text': s.text,
		'--muted': s.muted,
		'--accent': d.accent,
		'--accent-text': d.onAccent,
		'--success': s.success,
		'--warning': s.warning,
		'--danger': s.error,
		'--border': d.border,
		'--border-strong': d.borderStrong,
		'--hover': d.hover,
		'--pressed': d.pressed,
		'--selection': d.selection,
		'--selection-text': d.selectionText,
		'--disabled': d.disabled,
		'--scroll': d.scroll,
		'--scroll-hover': d.scrollHover,
		'--link': d.link,
		'--card': d.card,
		'--card-border': d.cardBorder,
		'--cork': d.corkBackground
	};
}

export { contrast };
