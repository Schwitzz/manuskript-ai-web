import {
	DEFAULT_APPEARANCE,
	apply,
	load,
	sanitize,
	save,
	type Appearance
} from '#lib/themes/apply.ts';
import type { Scheme } from '#lib/themes/schemes.ts';

/** Reactive appearance settings. Changing any field restyles the page immediately. */
class AppearanceStore {
	value = $state<Appearance>({ ...DEFAULT_APPEARANCE });
	active = $state<Scheme | null>(null);
	private media: MediaQueryList | null = null;

	/** Call once in the browser. */
	init() {
		this.value = load(localStorage);
		this.media = window.matchMedia('(prefers-color-scheme: dark)');
		// "System" must follow the device live, e.g. when the phone switches at sunset.
		this.media.addEventListener('change', () => this.render());
		this.render();
	}

	private render() {
		this.active = apply(document.documentElement, this.value, this.media?.matches ?? true);
	}

	set(patch: Partial<Appearance>) {
		this.value = sanitize({ ...this.value, ...patch });
		save(localStorage, this.value);
		this.render();
	}
}

export const appearance = new AppearanceStore();
