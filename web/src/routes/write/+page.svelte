<script lang="ts">
	import AppShell from '#lib/components/AppShell.svelte';
	import InspectorPanel from '#lib/components/InspectorPanel.svelte';
	import NoProject from '#lib/components/NoProject.svelte';
	import AIStatusBar from '#lib/components/ai/AIStatusBar.svelte';
	import { ai } from '#lib/stores/ai.svelte.ts';
	import { appearance } from '#lib/stores/appearance.svelte.ts';
	import { call } from '#lib/api.ts';
	import { EditorView, keymap } from '@codemirror/view';
	import { EditorState, type Extension } from '@codemirror/state';
	import { markdown, markdownLanguage } from '@codemirror/lang-markdown';
	import {
		indentWithTab,
		history,
		historyKeymap,
		defaultKeymap,
		undo,
		redo
	} from '@codemirror/commands';
	import {
		highlightSpecialChars,
		drawSelection,
		highlightActiveLine,
		dropCursor,
		rectangularSelection,
		crosshairCursor,
		highlightActiveLineGutter
	} from '@codemirror/view';
	import { searchKeymap } from '@codemirror/search';
	import { autocompletion, closeBrackets, closeBracketsKeymap } from '@codemirror/autocomplete';
	import { lintKeymap } from '@codemirror/lint';
	import { readableMarkdownExtension } from '#lib/editor/readable-markdown.ts';
	import { project } from '#lib/stores/project.svelte.ts';
	import { auth } from '#lib/stores/auth.svelte.ts';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import {
		firstScene,
		flatten,
		flattenWithDepth,
		isChapterItem,
		toItems,
		type AssociatedNote,
		type LabelDef,
		type OutlineItem
	} from '#lib/outline.ts';
	import { onMount } from 'svelte';
	import {
		Bold,
		Italic,
		Strikethrough,
		Heading1,
		Heading2,
		Heading3,
		Quote,
		List,
		ListOrdered,
		Link as LinkIcon,
		Undo2,
		Redo2,
		Search,
		AlignLeft,
		AlignCenter,
		AlignRight,
		Save,
		Eye,
		Code,
		BookOpen,
		CornerDownLeft,
		MessageSquareQuote,
		Info,
		PanelLeft,
		Folder,
		FileText,
		StickyNote
	} from '@lucide/svelte';

	function typewriterMode(getActive: () => boolean): Extension {
		return EditorView.updateListener.of((update) => {
			if (!getActive()) return;
			if (update.selectionSet || update.docChanged) {
				const v = update.view;
				const selection = v.state.selection.main.head;
				const line = v.state.doc.lineAt(selection);
				const linePos = v.coordsAtPos(line.from);
				if (linePos) {
					const containerHeight = v.dom.clientHeight;
					const targetScrollY = linePos.top - containerHeight / 2;
					v.scrollDOM.scrollTo(0, targetScrollY);
				}
			}
		});
	}

	let currentProject = $derived(project.name);
	let docId = $state(0);
	let activeNoteId = $state<string | null>(null);
	let noScenes = $state(false);
	let title = $state('');
	let content = $state('');
	let view: EditorView | null = $state(null);
	let saving = $state(false);
	let saved = $state(true);
	let loading = $state(true);
	let error = $state('');
	let saveError = $state('');
	let wordCount = $state(0);
	let sessionGoal = $state(500);
	let sessionStartWordCount = $state(0);
	let sessionCount = $derived(Math.max(0, wordCount - sessionStartWordCount));
	let showToolbar = $state(true);
	let showTypewriter = $state(false);
	let readableMode = $state(false);
	let searchOpen = $state(false);
	let version = $state('');
	let lastSaved = $state<Date | null>(null);
	let saveTimer: ReturnType<typeof setTimeout> | null = null;
	let autosaveEnabled = $state(true);
	let outlineOpen = $state(false);
	let outlineTree = $state<OutlineItem[]>([]);
	let sceneInfo: OutlineItem | null = $state(null);
	let labels: LabelDef[] = $state([]);
	let statusList: string[] = $state([]);

	let spellCheckEnabled = $derived(appearance.editorPrefs.spellCheck);
	let showWordCount = $derived(appearance.editorPrefs.showWordCount);
	let inspectorOpen = $derived(appearance.editorPrefs.showInspector);

	let flatOutline = $derived(flattenWithDepth(outlineTree, 0, labels));

	interface DocDropdownEntry {
		key: string;
		itemId: number;
		noteId: string | null;
		label: string;
		kind: 'chapter' | 'scene' | 'note';
	}

	let dropdownEntries = $derived.by<DocDropdownEntry[]>(() => {
		const entries: DocDropdownEntry[] = [];
		for (const { item, depth } of flatOutline) {
			const pad = '\u00A0\u00A0'.repeat(depth);
			if (item.type !== 'folder') {
				const isChap = isChapterItem(item, labels);
				entries.push({
					key: `doc:${item.id}`,
					itemId: item.id,
					noteId: null,
					label: `${pad}${isChap ? '📖 ' : '📄 '}${item.title || 'Untitled'}`,
					kind: isChap ? 'chapter' : 'scene'
				});
			}
			for (const note of item.associated_notes ?? []) {
				entries.push({
					key: `note:${item.id}:${note.id}`,
					itemId: item.id,
					noteId: note.id,
					label: `${pad}\u00A0\u00A0📝 Note: ${note.title || 'Untitled Note'} (${item.title})`,
					kind: 'note'
				});
			}
		}
		return entries;
	});

	let selectedDropdownKey = $derived(
		activeNoteId ? `note:${docId}:${activeNoteId}` : `doc:${docId}`
	);

	onMount(async () => {
		if (!auth.status?.authenticated) {
			goto('/login', { replaceState: true });
			return;
		}
		try {
			readableMode = localStorage.getItem('msk_readable_mode') === '1';
			outlineOpen = localStorage.getItem('msk_write_outline') === '1';
		} catch {}
		if (!project.name) {
			await project.fetchProjects();
		}
		await loadDocument();
	});

	function toggleOutlineSidebar() {
		outlineOpen = !outlineOpen;
		try {
			localStorage.setItem('msk_write_outline', outlineOpen ? '1' : '0');
		} catch {}
	}

	async function resolveScene(preferredId?: number): Promise<number | null> {
		const [o, l] = await Promise.all([
			call('GET /api/projects/{name}/outline', { params: { name: currentProject! } }),
			call('GET /api/projects/{name}/labels', { params: { name: currentProject! } })
		]);
		const items = toItems(o.items);
		outlineTree = items;
		labels = l.labels;
		statusList = l.status;
		const wanted = preferredId ?? Number(page.url.searchParams.get('scene'));
		const allItems = flatten(items);
		const scene =
			(wanted && allItems.find((i) => i.id === wanted && i.type !== 'folder')) ||
			(wanted && allItems.find((i) => i.id === wanted)) ||
			firstScene(items);
		sceneInfo = scene;
		return scene ? scene.id : null;
	}

	function buildExtensions(): Extension[] {
		return [
			EditorView.lineWrapping,
			highlightSpecialChars(),
			drawSelection(),
			dropCursor(),
			EditorView.updateListener.of((update) => {
				if (update.docChanged) {
					content = update.state.doc.toString();
					wordCount = countWords(content);
					debouncedSave();
				}
			}),
			highlightActiveLineGutter(),
			highlightActiveLine(),
			rectangularSelection(),
			crosshairCursor(),
			autocompletion(),
			closeBrackets(),
			keymap.of([
				...defaultKeymap,
				...historyKeymap,
				...searchKeymap,
				...closeBracketsKeymap,
				...lintKeymap,
				indentWithTab,
				{
					key: 'Mod-f',
					run: () => {
						searchOpen = true;
						return true;
					},
					preventDefault: true
				},
				{
					key: 'Escape',
					run: () => {
						if (searchOpen) {
							searchOpen = false;
							return true;
						}
						return false;
					}
				},
				{
					key: 'Ctrl-s',
					run: () => {
						forceSave();
						return true;
					},
					preventDefault: true
				}
			]),
			history(),
			markdown({ base: markdownLanguage, codeLanguages: undefined }),
			readableMarkdownExtension(() => readableMode),
			typewriterMode(() => showTypewriter),
			EditorView.theme({
				'&': { height: '100%', fontSize: '16px', lineHeight: '1.75', color: 'var(--text)' },
				'.cm-content': {
					padding: '24px 0 64px 0',
					caretColor: 'var(--accent)',
					fontFamily: "'Georgia', serif"
				},
				'.cm-scroller': { fontFamily: "'Georgia', serif", overflow: 'auto' },
				'.cm-gutters': { background: 'transparent', borderRight: 'none', color: 'var(--muted)' },
				'.cm-activeLine': { background: 'transparent' },
				'.cm-activeLineGutter': { background: 'transparent' },
				'.cm-cursor': { borderLeftColor: 'var(--accent)' },
				'.cm-selectionBackground': { background: 'var(--selection)' },
				'.cm-panel': {
					background: 'var(--surface)',
					border: '1px solid var(--border)',
					color: 'var(--text)',
					borderRadius: '8px'
				},
				'.cm-tooltip': {
					background: 'var(--surface)',
					border: '1px solid var(--border)',
					color: 'var(--text)'
				},
				'.cm-readable-h1': { fontSize: '1.65em', fontWeight: '700', color: 'var(--accent)' },
				'.cm-readable-h2': { fontSize: '1.4em', fontWeight: '700', color: 'var(--accent)' },
				'.cm-readable-h3': { fontSize: '1.2em', fontWeight: '600', color: 'var(--accent)' },
				'.cm-readable-h4': { fontSize: '1.08em', fontWeight: '600', color: 'var(--accent)' },
				'.cm-readable-bold': { fontWeight: '700' },
				'.cm-readable-italic': { fontStyle: 'italic' },
				'.cm-readable-strike': { textDecoration: 'line-through', opacity: '0.75' },
				'.cm-readable-code': {
					fontFamily: 'monospace',
					background: 'var(--surface)',
					padding: '0.1em 0.3em',
					borderRadius: '4px'
				},
				'.cm-readable-quote': {
					fontStyle: 'italic',
					color: 'var(--muted)',
					borderLeft: '3px solid var(--accent)',
					paddingLeft: '0.5rem'
				}
			})
		];
	}

	function countWords(text: string): number {
		return text
			.trim()
			.split(/\s+/)
			.filter((w) => w.length > 0).length;
	}

	function debouncedSave() {
		if (!autosaveEnabled || saving) return;
		if (saveTimer) clearTimeout(saveTimer);
		saved = false;
		saveTimer = setTimeout(() => forceSave(), 1000);
	}

	function applySpellCheck() {
		if (!view) return;
		view.dom.setAttribute('spellcheck', spellCheckEnabled ? 'true' : 'false');
		const contentEditable = view.dom.querySelector('.cm-content');
		if (contentEditable) {
			contentEditable.setAttribute('spellcheck', spellCheckEnabled ? 'true' : 'false');
		}
	}

	async function forceSave() {
		if (saveTimer) {
			clearTimeout(saveTimer);
			saveTimer = null;
		}
		if (!currentProject || !docId) return;
		saving = true;
		saveError = '';
		try {
			if (activeNoteId && sceneInfo) {
				const updatedNotes: AssociatedNote[] = (sceneInfo.associated_notes ?? []).map((n) =>
					n.id === activeNoteId ? { ...n, text: content } : n
				);
				sceneInfo.associated_notes = updatedNotes;
				await call('PATCH /api/projects/{name}/outline/{item_id}/fields', {
					params: { name: currentProject, item_id: docId },
					body: { associated_notes: updatedNotes } as any
				});
				lastSaved = new Date();
				saved = true;
			} else {
				const res = await call('PUT /api/projects/{name}/documents/{item_id}', {
					params: { name: currentProject, item_id: docId },
					body: { text: content, base_version: version }
				});
				version = (res as any).version;
				lastSaved = new Date();
				saved = true;
			}
		} catch (e: any) {
			saved = false;
			if (e?.status === 409 || String(e?.message || '').includes('409')) {
				// Version changed on disk (e.g., Desktop autosaved): adopt new base_version and retry save
				const detailVer = e?.detail?.version;
				if (typeof detailVer === 'string' && detailVer) {
					version = detailVer;
					try {
						const retryRes = await call('PUT /api/projects/{name}/documents/{item_id}', {
							params: { name: currentProject, item_id: docId },
							body: { text: content, base_version: version }
						});
						version = (retryRes as any).version;
						lastSaved = new Date();
						saved = true;
						saveError = '';
						return;
					} catch {}
				}
				try {
					const fresh = await call('GET /api/projects/{name}/documents/{item_id}', {
						params: { name: currentProject, item_id: docId }
					});
					version = fresh.version;
					const retryRes = await call('PUT /api/projects/{name}/documents/{item_id}', {
						params: { name: currentProject, item_id: docId },
						body: { text: content, base_version: version }
					});
					version = (retryRes as any).version;
					lastSaved = new Date();
					saved = true;
					saveError = '';
					return;
				} catch {}
			} else if (e?.status === 423) {
				// Project lock held briefly by Desktop: retry automatically in 1s
				saveTimer = setTimeout(() => forceSave(), 1000);
				return;
			}
			saveError = e?.message || 'Save failed';
		} finally {
			saving = false;
		}
	}

	/**
	 * Toggle inline Markdown formatting (`**`, `*`, `~~`).
	 * If the selection or characters immediately surrounding the cursor already have `before`/`after`,
	 * unwraps them instead of stacking `**** ****`.
	 */
	function insertMarkdown(before: string, after: string = before) {
		if (!view) return;
		const state = view.state;
		const sel = state.selection.main;
		const from = sel.from;
		const to = sel.to;
		const selected = state.sliceDoc(from, to);
		const bLen = before.length;
		const aLen = after.length;

		// 1. Check if selected text itself starts with `before` and ends with `after`
		const isSingleStar = before === '*';
		const startsWithDoubleStar = selected.startsWith('**') && !selected.startsWith('***');
		if (
			selected.length >= bLen + aLen &&
			selected.startsWith(before) &&
			selected.endsWith(after) &&
			!(isSingleStar && startsWithDoubleStar)
		) {
			const unwrapped = selected.slice(bLen, selected.length - aLen);
			view.dispatch(
				state.update({
					changes: { from, to, insert: unwrapped },
					selection: { anchor: from, head: from + unwrapped.length }
				})
			);
			view.focus();
			return;
		}

		// 2. Check if the document immediately outside [from, to] has `before` and `after`
		const outerBefore = from >= bLen ? state.sliceDoc(from - bLen, from) : '';
		const outerAfter = state.sliceDoc(to, to + aLen);
		const outerBefore2 = from >= 2 ? state.sliceDoc(from - 2, from) : '';
		const outerBefore3 = from >= 3 ? state.sliceDoc(from - 3, from) : '';
		const notDoubleStarConflict = !(isSingleStar && outerBefore2 === '**' && outerBefore3 !== '***');

		if (outerBefore === before && outerAfter === after && notDoubleStarConflict) {
			view.dispatch(
				state.update({
					changes: { from: from - bLen, to: to + aLen, insert: selected },
					selection: { anchor: from - bLen, head: to - bLen }
				})
			);
			view.focus();
			return;
		}

		// 3. Otherwise wrap with `before` and `after`
		view.dispatch(
			state.update({
				changes: { from, to, insert: before + selected + after },
				selection: { anchor: from + bLen, head: from + bLen + selected.length }
			})
		);
		view.focus();
	}

	/**
	 * Toggle block Markdown prefix (`# `, `## `, `### `, `> `, `- `, `1. `).
	 * Clicking the same block button a second time removes the prefix.
	 */
	function insertBlock(type: string) {
		if (!view) return;
		const state = view.state;
		const line = state.doc.lineAt(state.selection.main.from);
		const prefixes: Record<string, string> = {
			quote: '> ',
			list: '- ',
			ordered: '1. ',
			h1: '# ',
			h2: '## ',
			h3: '### '
		};
		const prefix = prefixes[type] || '';
		if (!prefix) return;

		if (line.text.startsWith(prefix)) {
			// Toggle OFF existing block prefix
			view.dispatch(
				state.update({
					changes: { from: line.from, to: line.from + prefix.length, insert: '' }
				})
			);
		} else {
			// Strip any other leading block prefix before applying the new one
			const existingMatch = /^(#{1,6}\s+|>\s+|[-*+]\s+|\d+\.\s+)/.exec(line.text);
			const replaceLen = existingMatch ? existingMatch[1].length : 0;
			view.dispatch(
				state.update({
					changes: { from: line.from, to: line.from + replaceLen, insert: prefix },
					selection: { anchor: line.from + prefix.length }
				})
			);
		}
		view.focus();
	}

	function alignText(alignment: 'left' | 'center' | 'right') {
		if (!view) return;
		const state = view.state;
		const line = view.state.doc.lineAt(state.selection.main.from);
		const text = line.text;
		const trimmed = text.replace(/^\s+/, '');
		const aligned =
			alignment === 'left'
				? trimmed
				: alignment === 'center'
					? '    ' + trimmed
					: '        ' + trimmed;
		view.dispatch(
			state.update({ changes: { from: line.from, to: line.from + text.length, insert: aligned } })
		);
		view.focus();
	}

	function insertAtCursor(text: string) {
		if (!view) return;
		const pos = view.state.selection.main.head;
		view.dispatch(
			view.state.update({
				changes: { from: pos, to: pos, insert: text },
				selection: { anchor: pos + text.length }
			})
		);
		view.focus();
	}

	function insertAIReply() {
		const { currentText } = ai.streaming;
		const lastAssistant = [...ai.messages].reverse().find((m) => m.role === 'assistant')?.content;
		const toInsert = currentText || lastAssistant;
		if (!toInsert) return;
		insertAtCursor(toInsert + '\n');
	}

	function askAboutSelection() {
		const viewRef = view;
		if (!viewRef) return;
		const sel = viewRef.state.selection.main;
		const selected = viewRef.state.sliceDoc(sel.from, sel.to);
		if (!selected.trim()) return;
		ai.panelOpen = true;
		if (!ai.initialized) void ai.init();
		ai.send(`Please help me with the following text:\n\n"${selected}"\n\nProvide your response.`);
	}

	function insertLink() {
		if (!view) return;
		const state = view.state;
		const sel = state.selection.main;
		const from = sel.from;
		const to = sel.to;
		const selected = state.sliceDoc(from, to);
		const url = prompt('Enter URL:', selected.startsWith('http') ? selected : 'https://');
		if (url === null) return;
		const display = selected || url;
		view.dispatch(
			state.update({
				changes: { from, to, insert: `[${display}](${url})` },
				selection: {
					anchor: from + display.length + 3,
					head: from + display.length + 3 + url.length
				}
			})
		);
		view.focus();
	}

	function toggleTypewriter() {
		showTypewriter = !showTypewriter;
		// Fix #9: hide toolbar when Focus is ON, and restore toolbar when Focus is untoggled OFF
		showToolbar = !showTypewriter;
	}

	function toggleReadableMode() {
		readableMode = !readableMode;
		try {
			localStorage.setItem('msk_readable_mode', readableMode ? '1' : '0');
		} catch {}
		if (view) {
			view.dispatch({});
		}
	}

	async function switchDocumentBySelection(val: string) {
		if (!saved) {
			await forceSave();
		}
		if (val.startsWith('note:')) {
			const parts = val.split(':');
			const itemId = Number(parts[1]);
			const noteId = parts.slice(2).join(':');
			await loadDocument(itemId, noteId);
		} else if (val.startsWith('doc:')) {
			const itemId = Number(val.slice(4));
			await loadDocument(itemId, null);
		}
	}

	async function loadDocument(
		targetDocId?: number,
		targetNoteId: string | null = null,
		retried = false
	) {
		if (!currentProject) {
			error = '';
			loading = false;
			return;
		}
		try {
			if (view) {
				view.destroy();
				view = null;
			}
			loading = true;
			error = '';
			saveError = '';
			const id = await resolveScene(targetDocId);
			if (id === null) {
				noScenes = true;
				loading = false;
				return;
			}
			noScenes = false;
			docId = id;
			activeNoteId = targetNoteId;
			ai.sceneId = id;

			if (targetNoteId && sceneInfo) {
				const note = (sceneInfo.associated_notes ?? []).find((n) => n.id === targetNoteId);
				if (note) {
					title = `${note.title} (${sceneInfo.title})`;
					content = note.text || '';
					version = '';
					wordCount = countWords(content);
					sessionStartWordCount = wordCount;
					loading = false;
					return;
				}
				activeNoteId = null;
			}

			const doc = await call('GET /api/projects/{name}/documents/{item_id}', {
				params: { name: currentProject!, item_id: docId }
			});
			title = doc.title;
			content = doc.text || '';
			version = doc.version;
			wordCount = countWords(content);
			sessionStartWordCount = wordCount;
			loading = false;
		} catch (e: any) {
			const isNotFound =
				e?.status === 404 ||
				String(e?.message || '')
					.toLowerCase()
					.includes('not found');
			if (isNotFound && !retried) {
				// Stored project name does not exist on this server: check available server projects
				const list = await project.fetchProjects();
				if (list.length > 0 && project.name) {
					await loadDocument(undefined, null, true);
					return;
				}
				project.select('');
				error = '';
				loading = false;
				return;
			}
			if (isNotFound) {
				project.select('');
				error = '';
				loading = false;
				return;
			}
			error = e.message || 'Failed to load document';
			loading = false;
		}
	}

	function initEditor() {
		if (view) view.destroy();
		const state = EditorState.create({ doc: content, extensions: buildExtensions() });
		const container = document.getElementById('editor-container');
		if (!container) return;
		view = new EditorView({ state, parent: container });
		view.focus();
		applySpellCheck();
	}

	$effect(() => {
		if (currentProject && !loading && !error && !noScenes && view === null) {
			initEditor();
		}
	});

	$effect(() => {
		applySpellCheck();
	});

	$effect(() => {
		return () => {
			if (view) view.destroy();
			if (saveTimer) clearTimeout(saveTimer);
		};
	});

	let progressPct = $derived(Math.min(100, Math.round((sessionCount / sessionGoal) * 100)));
	const circumference = 2 * Math.PI * 22;
	let strokeDashoffset = $derived(circumference - (progressPct / 100) * circumference);
</script>

{#snippet docHeaderDropdown()}
	<div class="flex min-w-0 flex-1 items-center gap-2">
		<button
			type="button"
			class="tap rounded p-1.5"
			onclick={toggleOutlineSidebar}
			title="Toggle Project Outline"
			aria-label="Toggle Project Outline"
			aria-pressed={outlineOpen}
			style="color: {outlineOpen ? 'var(--accent)' : 'var(--muted)'}"
		>
			<PanelLeft size={18} />
		</button>
		<select
			aria-label="Select document"
			value={selectedDropdownKey}
			onchange={(e) => switchDocumentBySelection(e.currentTarget.value)}
			class="max-w-md min-w-[180px] flex-1 truncate rounded-lg border px-3 py-1.5 text-sm font-semibold"
			style="background: var(--bg); border-color: var(--border); color: var(--text)"
		>
			{#each dropdownEntries as entry (entry.key)}
				<option value={entry.key}>{entry.label}</option>
			{/each}
		</select>
	</div>
{/snippet}

{#if !currentProject || loading || noScenes || error}
	<AppShell title="Write">
		{#if !currentProject}
			<NoProject onProjectReady={() => loadDocument()} />
		{:else if loading}
			<div class="flex min-h-[60vh] items-center justify-center">
				<p style="color: var(--muted)">Loading document...</p>
			</div>
		{:else if noScenes}
			<div class="flex min-h-[60vh] flex-col items-center justify-center gap-4">
				<p style="color: var(--muted); font-size: 0.875rem;">This project has no scenes yet.</p>
				<button
					class="rounded-lg border px-4 py-2 text-sm"
					style="border-color: var(--border)"
					onclick={() => goto('/outline')}>Open the outline</button
				>
			</div>
		{:else if error}
			<NoProject notice={error} onProjectReady={() => loadDocument()} />
		{/if}
	</AppShell>
{:else}
	<AppShell title={title || 'Untitled'} headerContent={docHeaderDropdown} fullHeight={true}>
		<div class="flex h-full min-h-0 flex-col overflow-hidden">
			<!-- Compact Status Bar -->
			<div
				class="flex shrink-0 items-center gap-2 border-b px-3 py-1 text-xs"
				style="border-color: var(--border); background: var(--surface)"
			>
				{#if saving}
					<span class="h-2 w-2 animate-pulse rounded-full" style="background: var(--warning)"></span>
					<span style="color: var(--muted)">Saving...</span>
				{:else if saved}
					<span class="h-2 w-2 rounded-full" style="background: var(--success)"></span>
					<span style="color: var(--muted)"
						>Saved{lastSaved ? ' ' + lastSaved.toLocaleTimeString() : ''}</span
					>
				{:else}
					<span class="h-2 w-2 rounded-full" style="background: var(--danger)"></span>
					<span style="color: var(--danger)">{saveError || 'Unsaved changes'}</span>
				{/if}
				<div class="h-3 w-px" style="background: var(--border)"></div>
				<span style="color: var(--muted)">{wordCount.toLocaleString()} words</span>
				<div class="h-3 w-px" style="background: var(--border)"></div>
				<div class="relative flex h-6 w-6 items-center justify-center">
					<svg class="absolute inset-0 h-full w-full -rotate-90" viewBox="0 0 48 48">
						<circle cx="24" cy="24" r="22" fill="none" stroke="var(--border)" stroke-width="3" />
						<circle
							cx="24"
							cy="24"
							r="22"
							fill="none"
							stroke="var(--accent)"
							stroke-width="3"
							stroke-linecap="round"
							stroke-dasharray={circumference}
							stroke-dashoffset={strokeDashoffset}
							class="transition-[stroke-dashoffset] duration-300"
						/>
					</svg>
					<span class="text-[8px] font-medium" style="color: var(--muted)"
						>{sessionCount}/{sessionGoal}</span
					>
				</div>
				<div class="flex-1"></div>
				{#if !showToolbar}
					<!-- Floating restore button when Focus Mode hides the main toolbar (#9) -->
					<button
						class="tap flex items-center gap-1 rounded border px-2 py-0.5 text-xs"
						type="button"
						onclick={toggleTypewriter}
						title="Exit Focus Mode and show toolbar"
						aria-label="Focus mode"
						aria-pressed={showTypewriter}
						style="border-color: var(--accent); color: var(--accent); background: var(--bg)"
					>
						<Eye size={14} />
						<span>Exit Focus</span>
					</button>
				{/if}
			</div>

			<!-- Categorized Main Toolbar with labels UNDER icon groups (#2, #3) -->
			{#if showToolbar}
				<div
					class="flex shrink-0 flex-wrap items-stretch gap-3 border-b px-3 py-1"
					style="border-color: var(--border); background: var(--surface)"
					role="toolbar"
					aria-label="Editor toolbar"
				>
					<!-- Category 1: Formatting -->
					<div
						class="flex flex-col items-center justify-between gap-0.5"
						role="group"
						aria-label="Formatting"
					>
						<div class="flex flex-wrap items-center gap-0.5">
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Undo"
								onclick={() => {
									if (view) undo({ state: view.state, dispatch: view.dispatch.bind(view) });
								}}><Undo2 size={17} style="color: var(--muted)" /></button
							>
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Redo"
								onclick={() => {
									if (view) redo({ state: view.state, dispatch: view.dispatch.bind(view) });
								}}><Redo2 size={17} style="color: var(--muted)" /></button
							>
							<div class="mx-1 h-4 w-px" style="background: var(--border)"></div>
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Heading 1 (toggle)"
								onclick={() => insertBlock('h1')}><Heading1 size={17} style="color: var(--muted)" /></button
							>
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Heading 2 (toggle)"
								onclick={() => insertBlock('h2')}><Heading2 size={17} style="color: var(--muted)" /></button
							>
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Heading 3 (toggle)"
								onclick={() => insertBlock('h3')}><Heading3 size={17} style="color: var(--muted)" /></button
							>
							<div class="mx-1 h-4 w-px" style="background: var(--border)"></div>
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Bold (toggle **)"
								onclick={() => insertMarkdown('**', '**')}><Bold size={17} style="color: var(--muted)" /></button
							>
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Italic (toggle *)"
								onclick={() => insertMarkdown('*', '*')}><Italic size={17} style="color: var(--muted)" /></button
							>
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Strikethrough (toggle ~~)"
								onclick={() => insertMarkdown('~~', '~~')}
								><Strikethrough size={17} style="color: var(--muted)" /></button
							>
							<div class="mx-1 h-4 w-px" style="background: var(--border)"></div>
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Blockquote (toggle)"
								onclick={() => insertBlock('quote')}><Quote size={17} style="color: var(--muted)" /></button
							>
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Bullet list (toggle)"
								onclick={() => insertBlock('list')}><List size={17} style="color: var(--muted)" /></button
							>
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Numbered list (toggle)"
								onclick={() => insertBlock('ordered')}
								><ListOrdered size={17} style="color: var(--muted)" /></button
							>
							<div class="mx-1 h-4 w-px" style="background: var(--border)"></div>
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Align Left"
								onclick={() => alignText('left')}><AlignLeft size={17} style="color: var(--muted)" /></button
							>
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Align Center"
								onclick={() => alignText('center')}
								><AlignCenter size={17} style="color: var(--muted)" /></button
							>
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Align Right"
								onclick={() => alignText('right')}
								><AlignRight size={17} style="color: var(--muted)" /></button
							>
							<div class="mx-1 h-4 w-px" style="background: var(--border)"></div>
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Search in document"
								onclick={() => {
									searchOpen = !searchOpen;
								}}><Search size={17} style="color: var(--muted)" /></button
							>
							<button
								class="tap rounded p-1.5"
								type="button"
								title="Insert link"
								onclick={() => insertLink()}><LinkIcon size={17} style="color: var(--muted)" /></button
							>
							<!-- Icon-only Markdown / Readable toggle (#3) -->
							<button
								class="tap rounded p-1.5"
								type="button"
								onclick={toggleReadableMode}
								title={readableMode
									? 'Readable mode active (Markdown syntax hidden — click to show Markdown code)'
									: 'Markdown code visible (click to switch to Readable mode)'}
								aria-label="Toggle Markdown code or readable mode"
								aria-pressed={readableMode}
								style="background: {readableMode ? 'var(--accent)' : 'transparent'}; color: {readableMode
									? 'var(--accent-text)'
									: 'var(--muted)'}"
							>
								{#if readableMode}
									<BookOpen size={17} />
								{:else}
									<Code size={17} />
								{/if}
							</button>
							<button
								class="tap rounded p-1.5 disabled:opacity-50"
								type="button"
								title="Save document (Ctrl+S)"
								disabled={saving}
								onclick={forceSave}
							>
								{#if saving}
									<span
										class="h-4 w-4 animate-spin rounded-full"
										style="border: 2px solid var(--muted); border-top-color: transparent"
									></span>
								{:else}
									<Save size={17} style="color: var(--muted)" />
								{/if}
							</button>
						</div>
						<span
							class="text-[9px] leading-none font-semibold tracking-wider uppercase select-none"
							style="color: var(--muted)">Formatting</span
						>
					</div>

					<!-- Separator between Formatting and Assistant -->
					<div class="self-stretch w-px" style="background: var(--border)"></div>

					<!-- Category 2: Assistant (#2, #8) -->
					<div
						class="flex flex-col items-center justify-between gap-0.5"
						role="group"
						aria-label="Assistant"
					>
						<div class="flex items-center gap-0.5">
							<button
								class="tap rounded p-1.5"
								type="button"
								onclick={() => insertAIReply()}
								title="Insert AI reply at cursor"
								aria-label="Insert AI reply at cursor"
							>
								<CornerDownLeft size={17} style="color: var(--muted)" />
							</button>
							<button
								class="tap rounded p-1.5"
								type="button"
								onclick={() => askAboutSelection()}
								title="Ask AI about selection"
								aria-label="Ask AI about selection"
							>
								<MessageSquareQuote size={17} style="color: var(--muted)" />
							</button>
						</div>
						<span
							class="text-[9px] leading-none font-semibold tracking-wider uppercase select-none"
							style="color: var(--muted)">Assistant</span
						>
					</div>

					<!-- Separator between Assistant and Info -->
					<div class="self-stretch w-px" style="background: var(--border)"></div>

					<!-- Category 3: Info (#2, #3, #12, #14) -->
					<div
						class="flex flex-col items-center justify-between gap-0.5"
						role="group"
						aria-label="Info"
					>
						<div class="flex items-center gap-0.5">
							<button
								class="tap rounded p-1.5"
								type="button"
								onclick={toggleTypewriter}
								title="Focus mode (center active line & hide toolbar)"
								aria-label="Focus mode"
								aria-pressed={showTypewriter}
							>
								<Eye size={17} style="color: {showTypewriter ? 'var(--accent)' : 'var(--muted)'}" />
							</button>
							<button
								class="tap rounded p-1.5"
								type="button"
								onclick={() => appearance.setEditorPrefs({ showInspector: !inspectorOpen })}
								title="Toggle Inspector"
								aria-label="Inspector"
								aria-pressed={inspectorOpen}
							>
								<Info
									size={17}
									style="color: {inspectorOpen ? 'var(--accent)' : 'var(--muted)'}"
								/>
							</button>
						</div>
						<span
							class="text-[9px] leading-none font-semibold tracking-wider uppercase select-none"
							style="color: var(--muted)">Info</span
						>
					</div>
				</div>
			{/if}

			<!-- Middle Workspace: Left Togglable Outline (#18) + Static Padded Writing Window (#17, #26) + Right Inspector -->
			<div class="flex min-h-0 flex-1 overflow-hidden" style="background: var(--editor)">
				{#if outlineOpen}
					<aside
						class="flex w-64 shrink-0 flex-col border-r overflow-y-auto"
						style="border-color: var(--border); background: var(--surface)"
						aria-label="Project Outline"
					>
						<div
							class="flex items-center justify-between border-b px-3 py-2 text-xs font-semibold"
							style="border-color: var(--border); color: var(--muted)"
						>
							<span>PROJECT OUTLINE</span>
							<span>{outlineTree.reduce((n, i) => n + i.words, 0).toLocaleString()} w</span>
						</div>
						<ul class="flex flex-col gap-0.5 p-1.5 text-xs">
							{#each flatOutline as { item, depth } (item.id)}
								{@const isChap = isChapterItem(item, labels)}
								{@const activeDoc = docId === item.id && !activeNoteId}
								<li>
									<button
										type="button"
										disabled={item.type === 'folder'}
										onclick={() => loadDocument(item.id, null)}
										class="flex w-full items-center gap-1.5 rounded px-2 py-1.5 text-left transition-colors"
										style="padding-left: {depth * 14 + 8}px; background: {activeDoc
											? 'var(--accent)'
											: 'transparent'}; color: {activeDoc
											? 'var(--accent-text)'
											: item.type === 'folder'
												? 'var(--muted)'
												: 'var(--text)'}"
									>
										{#if item.type === 'folder'}
											<Folder size={14} class="shrink-0" />
										{:else if isChap}
											<BookOpen size={14} class="shrink-0" />
										{:else}
											<FileText size={14} class="shrink-0" />
										{/if}
										<span class="flex-1 truncate {isChap || item.type === 'folder' ? 'font-semibold' : ''}"
											>{item.title || 'Untitled'}</span
										>
										<span class="text-[10px] opacity-75">{item.words}</span>
									</button>
									{#if item.associated_notes?.length}
										<ul class="flex flex-col gap-0.5">
											{#each item.associated_notes as note (note.id)}
												{@const activeNote = docId === item.id && activeNoteId === note.id}
												<li>
													<button
														type="button"
														onclick={() => loadDocument(item.id, note.id)}
														class="flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-[11px]"
														style="padding-left: {(depth + 1) * 14 + 8}px; background: {activeNote
															? 'var(--accent)'
															: 'transparent'}; color: {activeNote
															? 'var(--accent-text)'
															: 'var(--muted)'}"
													>
														<StickyNote size={12} class="shrink-0" />
														<span class="flex-1 truncate">{note.title || 'Note'}</span>
													</button>
												</li>
											{/each}
										</ul>
									{/if}
								</li>
							{/each}
						</ul>
					</aside>
				{/if}

				<!-- Static Writing Column with Comfortable Reading Padding (#17, #26) -->
				<div class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
					<div
						class="mx-auto flex h-full w-full max-w-4xl flex-1 flex-col overflow-hidden px-6 sm:px-14"
						id="editor-container"
					></div>
				</div>

				<!-- Right Docked Inspector Panel -->
				{#if inspectorOpen && sceneInfo && currentProject}
					<aside
						class="w-72 shrink-0 overflow-y-auto border-l p-2"
						style="border-color: var(--border); background: var(--surface)"
					>
						<InspectorPanel scene={sceneInfo} {labels} {statusList} project={currentProject} />
					</aside>
				{/if}
			</div>

			<!-- AI Streaming Status -->
			<AIStatusBar />

			<!-- Footer -->
			{#if showWordCount}
				<div
					class="flex shrink-0 items-center justify-between border-t px-4 py-1.5 text-xs"
					style="border-color: var(--border); background: var(--surface); color: var(--muted)"
				>
					<span>{wordCount.toLocaleString()} words</span>
					<span>Tab inserts tab</span>
				</div>
			{/if}
		</div>
	</AppShell>
{/if}
