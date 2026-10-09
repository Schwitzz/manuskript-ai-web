// Colour maths ported from the desktop fork (manuskript/appearance/colors.py).
// Tested against values exported from the Python original, so the two cannot drift apart.

export type Rgb = [number, number, number];

export function toRgb(hex: string): Rgb {
	let h = hex.replace(/^#/, '');
	if (h.length === 3) h = [...h].map((c) => c + c).join('');
	return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)) as Rgb;
}

// Python's round() is banker's rounding (halves go to the even number); match it exactly.
function pyRound(v: number): number {
	const f = Math.floor(v);
	const d = v - f;
	if (d < 0.5) return f;
	if (d > 0.5) return f + 1;
	return f % 2 === 0 ? f : f + 1;
}

export function toHex(rgb: number[]): string {
	return (
		'#' +
		rgb
			.map((v) => Math.max(0, Math.min(255, pyRound(v))))
			.map((v) => v.toString(16).padStart(2, '0'))
			.join('')
	);
}

/** Blend: f=0 gives c1, f=1 gives c2. */
export function mix(c1: string, c2: string, f = 0.5): string {
	const a = toRgb(c1);
	const b = toRgb(c2);
	return toHex(a.map((v, i) => v + (b[i] - v) * f));
}

export function luminance(c: string): number {
	const ch = (v: number) => {
		v /= 255;
		return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
	};
	const [r, g, b] = toRgb(c).map(ch);
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** WCAG contrast ratio, 1 to 21. */
export function contrast(c1: string, c2: string): number {
	let l1 = luminance(c1);
	let l2 = luminance(c2);
	if (l1 < l2) [l1, l2] = [l2, l1];
	return (l1 + 0.05) / (l2 + 0.05);
}

/** White or black, whichever reads better on `bg`. */
export function readableOn(bg: string, light = '#ffffff', dark = '#000000'): string {
	return contrast(bg, light) >= contrast(bg, dark) ? light : dark;
}

/** Nudge `fg` towards white/black until it reaches `minRatio` on `bg`. */
export function ensureContrast(fg: string, bg: string, minRatio: number): string {
	const target = luminance(bg) < 0.5 ? '#ffffff' : '#000000';
	let out = fg;
	for (let i = 1; i <= 20; i++) {
		if (contrast(out, bg) >= minRatio) break;
		out = mix(fg, target, i * 0.05);
	}
	return out;
}
