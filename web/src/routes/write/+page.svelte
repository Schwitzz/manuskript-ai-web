<script lang="ts">
import AppShell from '#lib/components/AppShell.svelte';
import InspectorPanel from '#lib/components/InspectorPanel.svelte';
import AIChatPanel from '#lib/components/ai/AIChatPanel.svelte';
import AIStatusBar from '#lib/components/ai/AIStatusBar.svelte';
import { ai } from '#lib/stores/ai.svelte.ts';
import { call } from '#lib/api.ts';
import { EditorView, keymap } from '@codemirror/view';
import { EditorState } from '@codemirror/state';
import { markdown, markdownLanguage } from '@codemirror/lang-markdown';
import { indentWithTab, history, historyKeymap, defaultKeymap, undo, redo } from '@codemirror/commands';
import { highlightSpecialChars, drawSelection, highlightActiveLine, dropCursor, rectangularSelection, crosshairCursor, highlightActiveLineGutter } from '@codemirror/view';
import { searchKeymap } from '@codemirror/search';
import { autocompletion, closeBrackets, closeBracketsKeymap } from '@codemirror/autocomplete';
import { lintKeymap } from '@codemirror/lint';
import type { Extension } from '@codemirror/state';
import { project } from '#lib/stores/project.svelte.ts';
import { auth } from '#lib/stores/auth.svelte.ts';
import { goto } from '$app/navigation';
import { page } from '$app/state';
import { firstScene, flatten, toItems, type LabelDef, type OutlineItem } from '#lib/outline.ts';
import { onMount } from 'svelte';

// Typewriter mode: keeps the cursor line vertically centered in the viewport
function typewriterMode(): Extension {
return EditorView.updateListener.of((update) => {
if (update.selectionSet || update.docChanged) {
const view = update.view;
const selection = view.state.selection.main.head;
const line = view.state.doc.lineAt(selection);
const linePos = view.coordsAtPos(line.from);
if (linePos) {
const containerHeight = view.dom.clientHeight;
const targetScrollY = linePos.top - containerHeight / 2;
view.scrollDOM.scrollTo(0, targetScrollY);
}
}
});
}

// Focus mode: dims lines not near the active selection
function focusModeExtension(mode: 'none' | 'line'): Extension {
return EditorView.updateListener.of(() => {
// Line focus mode is handled by highlightActiveLine in buildExtensions
// Paragraph focus would require complex decoration logic - skipping for now
});
}
import { Bold, Italic, Strikethrough, Heading1, Heading2, Heading3, Quote, List, ListOrdered, Link as LinkIcon, Undo2, Redo2, Search, Type, AlignLeft, AlignCenter, AlignRight, Save, Eye, Check, Sparkles, Info } from '@lucide/svelte';

let currentProject = $derived(project.name);
let docId = $state(0);
let noScenes = $state(false);
let title = $state('');
let content = $state('');
let view: EditorView | null = $state(null);
let saving = $state(false);
let saved = $state(true);
let loading = $state(true);
let error = $state('');
let wordCount = $state(0);
let sessionGoal = $state(500);
let sessionStartWordCount = $state(0);
let sessionCount = $derived(Math.max(0, wordCount - sessionStartWordCount));
let showToolbar = $state(true);
let showWordCount = $state(true);
let showTypewriter = $state(false);
let focusMode = $state<'none' | 'line'>('none');
let searchOpen = $state(false);
let version = $state('');
let lastSaved = $state<Date | null>(null);
let saveTimer: ReturnType<typeof setTimeout> | null = null;
let autosaveEnabled = $state(true);
let spellCheckEnabled = $state(true);
let inspectorOpen = $state(false);
let sceneInfo: OutlineItem | null = $state(null);
let labels: LabelDef[] = $state([]);
let statusList: string[] = $state([]);

// Redirect to login if not authenticated
onMount(async () => {
	if (!auth.status?.authenticated) {
		goto('/login', { replaceState: true });
		return;
	}
	await loadDocument();
});

/** Load the outline and labels, then decide which scene to open: ?scene=<id> if it is a real
 *  scene, otherwise the first scene in reading order. Returns null for a project with none. */
async function resolveScene(): Promise<number | null> {
	const [o, l] = await Promise.all([
		call('GET /api/projects/{name}/outline', { params: { name: currentProject! } }),
		call('GET /api/projects/{name}/labels', { params: { name: currentProject! } })
	]);
	const items = toItems(o.items);
	labels = l.labels;
	statusList = l.status;
	const wanted = Number(page.url.searchParams.get('scene'));
	const scene = (wanted && flatten(items).find((i) => i.id === wanted && i.type !== 'folder')) || firstScene(items);
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
{ key: 'Mod-f', run: () => { searchOpen = true; return true; }, preventDefault: true },
{ key: 'Escape', run: () => { if (searchOpen) { searchOpen = false; return true; } return false; } },
{ key: 'Ctrl-s', run: () => { forceSave(); return true; }, preventDefault: true }
]),
history(),
markdown({ base: markdownLanguage, codeLanguages: undefined }),
typewriterMode(),
focusModeExtension(focusMode),
EditorView.theme({
'&': { height: '100%', fontSize: '16px', lineHeight: '1.75', color: 'var(--text)' },
'.cm-content': { padding: '16px 0', caretColor: 'var(--accent)', fontFamily: "'Georgia', serif" },
'.cm-scroller': { fontFamily: "'Georgia', serif" },
'.cm-gutters': { background: 'transparent', borderRight: 'none', color: 'var(--muted)' },
'.cm-activeLine': { background: 'transparent' },
'.cm-activeLineGutter': { background: 'transparent' },
'.cm-cursor': { borderLeftColor: 'var(--accent)' },
'.cm-selectionBackground': { background: 'var(--selection)' },
'.cm-panel': { background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: '8px' },
'.cm-tooltip': { background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' },
'.cm-focusDim': { opacity: '0.25', filter: 'blur(0.3px)' },
'.cm-focusLine': { background: 'var(--accent)', color: 'var(--accent-bg)' }
})
];
}

function countWords(text: string): number {
return text.trim().split(/\s+/).filter(w => w.length > 0).length;
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
if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; }
saving = true;
try {
const res = await call('PUT /api/projects/{name}/documents/{item_id}', {
params: { name: currentProject!, item_id: docId },
body: { text: content, base_version: version }
});
version = (res as any).version;
lastSaved = new Date();
saved = true;
} catch (e: any) {
saved = false;
if (e.message.includes('409')) {
try { await loadDocument(); } catch {}
} else {
error = e.message || 'Save failed';
}
} finally {
saving = false;
}
}

function insertMarkdown(before: string, after: string = '') {
if (!view) return;
const sel = view.state.selection;
const from = sel.main.from;
const to = sel.main.to;
const selected = view.state.sliceDoc(from, to);
view.dispatch(view.state.update({
changes: { from, to, insert: before + selected + after },
selection: { anchor: from + before.length, head: from + before.length + selected.length }
}));
view.focus();
}

function insertBlock(type: string) {
if (!view) return;
const state = view.state;
const line = view.state.doc.lineAt(state.selection.main.from);
const pos = line.from;
const prefixes: Record<string, string> = { quote: '> ', list: '- ', ordered: '1. ', h1: '# ', h2: '## ', h3: '### ' };
const prefix = prefixes[type] || '';
view.dispatch(state.update({
changes: { from: pos, to: pos, insert: prefix },
selection: { anchor: pos + prefix.length }
}));
view.focus();
}

function alignText(alignment: 'left' | 'center' | 'right') {
if (!view) return;
const state = view.state;
const line = view.state.doc.lineAt(state.selection.main.from);
const text = line.text;
const trimmed = text.replace(/^\s+/, '');
const aligned = alignment === 'left' ? trimmed : alignment === 'center' ? '    ' + trimmed : '        ' + trimmed;
view.dispatch(state.update({ changes: { from: line.from, to: line.from + text.length, insert: aligned } }));
view.focus();
}

function insertAtCursor(text: string) {
	if (!view) return;
	const pos = view.state.selection.main.head;
	view.dispatch(view.state.update({
		changes: { from: pos, to: pos, insert: text },
		selection: { anchor: pos + text.length }
	}));
	view.focus();
}

function insertAIReply() {
	const { currentText } = ai.streaming;
	if (!currentText) return;
	insertAtCursor(currentText + '\n');
}

function askAboutSelection() {
	const viewRef = view;
	if (!viewRef) return;
	const sel = viewRef.state.selection.main;
	const selected = viewRef.state.sliceDoc(sel.from, sel.to);
	if (!selected.trim()) return;
	ai.panelOpen = true;
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
if (url === null) return; // cancelled
const display = selected || url;
view.dispatch(state.update({
changes: { from, to, insert: `[${display}](${url})` },
selection: { anchor: from + display.length + 3, head: from + display.length + 3 + url.length }
}));
view.focus();
}

const focusModeLabels: Record<string, string> = { none: 'Focus', line: 'Line' };

function cycleFocusMode() {
const levels: Array<'none' | 'line'> = ['none', 'line'];
const idx = (levels.indexOf(focusMode) + 1) % levels.length;
focusMode = levels[idx];
}

function toggleTypewriter() {
showTypewriter = !showTypewriter;
if (showTypewriter) showToolbar = false; // hide toolbar for distraction-free mode
}

async function loadDocument() {
if (!currentProject) {
error = 'No project selected';
loading = false;
return;
}
try {
// Loading swaps the editor out of the page, so drop the old instance; the effect above
// builds a fresh one once the new text is in.
if (view) { view.destroy(); view = null; }
loading = true;
error = '';
const id = await resolveScene();
if (id === null) {
noScenes = true;
loading = false;
return;
}
noScenes = false;
docId = id;
ai.sceneId = id; // the assistant reads this scene's text, summary and POV
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

// Mount the editor once a scene has loaded. An empty scene (every new project starts with
// one) still needs an editor, so this must not depend on the text being non-empty.
$effect(() => {
if (currentProject && !loading && !error && !noScenes && view === null) {
initEditor();
}
});

$effect(() => {
applySpellCheck();
});

$effect(() => {
return () => { if (view) view.destroy(); if (saveTimer) clearTimeout(saveTimer); };
});

let progressPct = $derived(Math.min(100, Math.round((sessionCount / sessionGoal) * 100)));
const circumference = 2 * Math.PI * 22;
let strokeDashoffset = $derived(circumference - (progressPct / 100) * circumference);
</script>

{#if !currentProject || loading || noScenes || error}
<AppShell title="Write">
{#if !currentProject}
    <div class="flex min-h-[60vh] flex-col items-center justify-center gap-4">
        <p style="color: var(--muted); font-size: 0.875rem;">No project selected</p>
        <button class="rounded-lg border px-4 py-2 text-sm" style="border-color: var(--border)"
            onclick={() => goto('/more')}>Go to More → Create a project</button>
    </div>
{:else if loading}
    <div class="flex min-h-[60vh] items-center justify-center">
        <p style="color: var(--muted)">Loading document...</p>
    </div>
{:else if noScenes}
    <div class="flex min-h-[60vh] flex-col items-center justify-center gap-4">
        <p style="color: var(--muted); font-size: 0.875rem;">This project has no scenes yet.</p>
        <button class="rounded-lg border px-4 py-2 text-sm" style="border-color: var(--border)"
            onclick={() => goto('/outline')}>Open the outline</button>
    </div>
{:else if error}
    <div class="flex min-h-[60vh] flex-col items-center justify-center gap-4">
        <p role="alert" style="color: var(--danger)">{error}</p>
        {#if error.toLowerCase().includes('404')}
            <p style="color: var(--muted); font-size: 0.875rem;">Project may not exist. Create a new project or select another.</p>
            <button class="rounded-lg border px-4 py-2 text-sm" style="border-color: var(--border)"
                onclick={() => goto('/more')}>Create project</button>
        {:else}
            <button class="rounded-lg border px-4 py-2 text-sm" style="border-color: var(--border)" onclick={loadDocument}>Retry</button>
        {/if}
    </div>
{/if}
</AppShell>
{:else}
    <AppShell title={title || 'Untitled'}>
<div class="flex flex-col">
<!-- Status bar -->
<div class="flex items-center gap-2 border-b px-3 py-1 text-xs" style="border-color: var(--border); background: var(--surface)">
{#if saving}
<span class="h-2 w-2 animate-pulse rounded-full" style="background: var(--warning)" />
<span style="color: var(--muted)">Saving...</span>
{:else if saved}
<span class="h-2 w-2 rounded-full" style="background: var(--success)" />
<span style="color: var(--muted)">Saved{lastSaved ? ' ' + lastSaved.toLocaleTimeString() : ''}</span>
{:else}
<span class="h-2 w-2 rounded-full" style="background: var(--danger)" />
<span style="color: var(--danger)">Unsaved changes</span>
{/if}
<div class="h-3 w-px" style="background: var(--border)" />
<span style="color: var(--muted)">{wordCount.toLocaleString()} words</span>
<div class="h-3 w-px" style="background: var(--border)" />
<div class="relative flex h-7 w-7 items-center justify-center">
<svg class="absolute inset-0 h-full w-full -rotate-90" viewBox="0 0 48 48">
<circle cx="24" cy="24" r="22" fill="none" stroke="var(--border)" stroke-width="3" />
<circle cx="24" cy="24" r="22" fill="none" stroke="var(--accent)" stroke-width="3" stroke-linecap="round"
stroke-dasharray={circumference} stroke-dashoffset={strokeDashoffset} class="transition-[stroke-dashoffset] duration-300" />
</svg>
<span class="text-[9px] font-medium" style="color: var(--muted)">{sessionCount}/{sessionGoal}</span>
</div>
<div class="flex-1" />
<button class="tap rounded p-1" type="button" onclick={toggleTypewriter}>
{#if showTypewriter}<Eye size={16} style="color: var(--accent)" />{:else}<Eye size={16} style="color: var(--muted)" />{/if}
</button>
<button class="tap rounded p-1" type="button" onclick={cycleFocusMode} title={focusModeLabels[focusMode]}>
<Type size={16} style="color: {focusMode !== 'none' ? 'var(--accent)' : 'var(--muted)'}" />
</button>
<button class="tap rounded p-1" type="button" onclick={() => spellCheckEnabled = !spellCheckEnabled} title="Spell check">
<Check size={16} style="color: {spellCheckEnabled ? 'var(--accent)' : 'var(--muted)'}" />
</button>
<button class="tap rounded p-1" type="button" onclick={() => showWordCount = !showWordCount}>
<Type size={16} style="color: {showWordCount ? 'var(--accent)' : 'var(--muted)'}" />
</button>
<button class="tap rounded p-1" type="button" onclick={() => inspectorOpen = !inspectorOpen} title="Inspector">
<Info size={16} style="color: {inspectorOpen ? 'var(--accent)' : 'var(--muted)'}" />
</button>
</div>
<!-- Formatting toolbar -->
{#if showToolbar}
<div class="flex flex-wrap items-center gap-0.5 border-b px-2 py-1.5" style="border-color: var(--border); background: var(--surface)" role="toolbar">
<button class="tap rounded p-1.5" type="button" onclick={() => { undo({ state: view!.state, dispatch: view!.dispatch.bind(view!)}); }}><Undo2 size={18} style="color: var(--muted)" /></button>
<button class="tap rounded p-1.5" type="button" onclick={() => { redo({ state: view!.state, dispatch: view!.dispatch.bind(view!)}); }}><Redo2 size={18} style="color: var(--muted)" /></button>
<div class="h-5 w-px mx-1" style="background: var(--border)" />
<button class="tap rounded p-1.5" type="button" onclick={() => insertBlock('h1')}><Heading1 size={18} style="color: var(--muted)" /></button>
<button class="tap rounded p-1.5" type="button" onclick={() => insertBlock('h2')}><Heading2 size={18} style="color: var(--muted)" /></button>
<button class="tap rounded p-1.5" type="button" onclick={() => insertBlock('h3')}><Heading3 size={18} style="color: var(--muted)" /></button>
<div class="h-5 w-px mx-1" style="background: var(--border)" />
<button class="tap rounded p-1.5" type="button" onclick={() => insertMarkdown('**', '**')}><Bold size={18} style="color: var(--muted)" /></button>
<button class="tap rounded p-1.5" type="button" onclick={() => insertMarkdown('*', '*')}><Italic size={18} style="color: var(--muted)" /></button>
<button class="tap rounded p-1.5" type="button" onclick={() => insertMarkdown('~~', '~~')}><Strikethrough size={18} style="color: var(--muted)" /></button>
<div class="h-5 w-px mx-1" style="background: var(--border)" />
<button class="tap rounded p-1.5" type="button" onclick={() => insertBlock('quote')}><Quote size={18} style="color: var(--muted)" /></button>
<button class="tap rounded p-1.5" type="button" onclick={() => insertBlock('list')}><List size={18} style="color: var(--muted)" /></button>
<button class="tap rounded p-1.5" type="button" onclick={() => insertBlock('ordered')}><ListOrdered size={18} style="color: var(--muted)" /></button>
<div class="h-5 w-px mx-1" style="background: var(--border)" />
<button class="tap rounded p-1.5" type="button" onclick={() => alignText('left')}><AlignLeft size={18} style="color: var(--muted)" /></button>
<button class="tap rounded p-1.5" type="button" onclick={() => alignText('center')}><AlignCenter size={18} style="color: var(--muted)" /></button>
<button class="tap rounded p-1.5" type="button" onclick={() => alignText('right')}><AlignRight size={18} style="color: var(--muted)" /></button>
<div class="h-5 w-px mx-1" style="background: var(--border)" />
<button class="tap rounded p-1.5" type="button" onclick={() => { searchOpen = !searchOpen; }}><Search size={18} style="color: var(--muted)" /></button>
<button class="tap rounded p-1.5" type="button" onclick={() => insertLink()}><LinkIcon size={18} style="color: var(--muted)" /></button>
<div class="h-5 w-px mx-1" style="background: var(--border)" />
<!-- AI editor extras -->
<button class="tap rounded p-1.5" type="button" onclick={() => insertAIReply()} title="Insert AI reply at cursor"><Sparkles size={18} style="color: var(--muted)" /></button>
<button class="tap rounded p-1.5" type="button" onclick={() => askAboutSelection()} title="Ask AI about selection"><Type size={18} style="color: var(--muted)" /></button>
<button class="tap rounded p-1.5" type="button" onclick={() => { ai.panelOpen = !ai.panelOpen; }} title="AI Chat"><Sparkles size={18} style="color: {ai.panelOpen ? 'var(--accent)' : 'var(--muted)'}" /></button>
<button class="tap rounded p-1.5 disabled:opacity-50" type="button" disabled={saving} onclick={forceSave}>
{#if saving}<span class="h-4 w-4 animate-spin rounded-full" style="border: 2px solid var(--muted); border-top-color: transparent" />{:else}<Save size={18} style="color: var(--muted)" />{/if}
</button>
</div>
{/if}
<!-- Editor -->
<div class="flex-1 overflow-hidden" id="editor-container" style="background: var(--editor)" />
<!-- Inspector Panel -->
{#if inspectorOpen && sceneInfo && currentProject}
<InspectorPanel scene={sceneInfo} {labels} {statusList} project={currentProject} />
{/if}
<!-- AI Streaming Status -->
<AIStatusBar />
<!-- Footer -->
{#if showWordCount}
<div class="flex items-center justify-between border-t px-4 py-1.5 text-xs" style="border-color: var(--border); background: var(--surface); color: var(--muted)">
<span>{wordCount.toLocaleString()} words</span>
<span>Tab inserts tab</span>
</div>
{/if}
</div>
</AppShell>
<!-- AI Chat Panel (sheet/drawer) -->
{#if ai.panelOpen}
	<div class="absolute right-0 top-14 z-30 flex h-[calc(100dvh-3.5rem)] w-[min(420px,85vw)] flex-col overflow-hidden border-l shadow-xl"
		style="border-color: var(--border); background: var(--surface)">
		<AIChatPanel />
	</div>
{/if}
{/if}
