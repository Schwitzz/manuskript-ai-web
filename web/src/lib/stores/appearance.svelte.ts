import {
	DEFAULT_APPEARANCE,
	apply,
	load,
	sanitize,
	save,
	type Appearance
} from '#lib/themes/apply.ts';
import type { Scheme } from '#lib/themes/schemes.ts';

export interface EditorAppearancePrefs {
	spellCheck: boolean;
	showWordCount: boolean;
	showInspector: boolean;
}

const PREFS_KEY = 'msk.editor_prefs';

function loadEditorPrefs(): EditorAppearancePrefs {
	try {
		const raw = localStorage.getItem(PREFS_KEY);
		if (!raw) return { spellCheck: true, showWordCount: true, showInspector: false };
		const parsed = JSON.parse(raw);
		return {
			spellCheck: typeof parsed.spellCheck === 'boolean' ? parsed.spellCheck : true,
			showWordCount: typeof parsed.showWordCount === 'boolean' ? parsed.showWordCount : true,
			showInspector: typeof parsed.showInspector === 'boolean' ? parsed.showInspector : false
		};
	} catch {
		return { spellCheck: true, showWordCount: true, showInspector: false };
	}
}

/** Reactive appearance settings. Changing any field restyles the page immediately. */
class AppearanceStore {
	value = $state<Appearance>({ ...DEFAULT_APPEARANCE });
	active = $state<Scheme | null>(null);
	editorPrefs = $state<EditorAppearancePrefs>({
		spellCheck: true,
		showWordCount: true,
		showInspector: false
	});
	private media: MediaQueryList | null = null;

	/** Call once in the browser. */
	init() {
		this.value = load(localStorage);
		this.editorPrefs = loadEditorPrefs();
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

	setEditorPrefs(patch: Partial<EditorAppearancePrefs>) {
		this.editorPrefs = { ...this.editorPrefs, ...patch };
		try {
			localStorage.setItem(PREFS_KEY, JSON.stringify(this.editorPrefs));
		} catch {}
	}
}

export const appearance = new AppearanceStore();
