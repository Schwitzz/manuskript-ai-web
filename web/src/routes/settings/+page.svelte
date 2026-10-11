<script lang="ts">
import AppShell from '#lib/components/AppShell.svelte';
import NoProject from '#lib/components/NoProject.svelte';
import { project } from '#lib/stores/project.svelte.ts';
import AppearanceSettings from '#lib/components/AppearanceSettings.svelte';
import { Palette, BookOpen, FileText, Save, Check } from '@lucide/svelte';
import { call } from '#lib/api';

const PROJECT_NAME = project.name ?? '';

let activeTab = $state<'general' | 'summary'>('general');
let saving = $state(false);
let saved = $state(true);
let error = $state('');

let bookInfo = $state<Record<string, string>>({});
let snowflakeSummary = $state<Record<string, string>>({});

let loading = $state(true);

const generalFields = [
{ key: 'title', label: 'Title', placeholder: 'Book title' },
{ key: 'series', label: 'Series', placeholder: 'Series name' },
{ key: 'series_number', label: 'Series Number', placeholder: 'e.g., 1' },
{ key: 'volume', label: 'Volume', placeholder: 'Volume name' },
{ key: 'genre', label: 'Genre', placeholder: 'e.g., Fantasy' },
{ key: 'subtitle', label: 'Subtitle', placeholder: 'Book subtitle' },
{ key: 'author', label: 'Author', placeholder: 'Your name' },
{ key: 'editor', label: 'Editor', placeholder: 'Editor name' },
{ key: 'publisher', label: 'Publisher', placeholder: 'Publisher name' },
{ key: 'website', label: 'Website', placeholder: 'https://...' },
{ key: 'email', label: 'Email', placeholder: 'your@email.com' },
{ key: 'license', label: 'License', placeholder: 'e.g., All rights reserved' },
];

const summaryFields = [
{ key: 'situation', label: 'Situation', placeholder: 'One paragraph describing the situation' },
{ key: 'sentence', label: 'Sentence', placeholder: 'One-sentence summary' },
{ key: 'paragraph', label: 'Paragraph', placeholder: 'One-paragraph summary' },
{ key: 'page', label: 'Page', placeholder: 'One-page summary' },
{ key: 'full', label: 'Full', placeholder: 'Full summary' },
];

async function loadData() {
if (!PROJECT_NAME) { loading = false; return; }
try {
loading = true;
error = '';
const data = await call('GET /api/projects/{name}/info', {
params: { name: PROJECT_NAME }
});
bookInfo = (data as any).info || {};
snowflakeSummary = (data as any).summary || {};
loading = false;
} catch (e: any) {
error = e.message || 'Failed to load settings';
loading = false;
}
}

async function saveInfo() {
try {
saving = true;
saved = false;
await call('PUT /api/projects/{name}/info', {
params: { name: PROJECT_NAME },
body: { values: bookInfo }
});
saved = true;
setTimeout(() => { saved = true; }, 2000);
} catch (e: any) {
error = e.message;
} finally {
saving = false;
}
}

async function saveSummary() {
try {
saving = true;
saved = false;
await call('PUT /api/projects/{name}/summary', {
params: { name: PROJECT_NAME },
body: { values: snowflakeSummary }
});
saved = true;
setTimeout(() => { saved = true; }, 2000);
} catch (e: any) {
error = e.message;
} finally {
saving = false;
}
}

function updateField(key: string, value: string) {
bookInfo = { ...bookInfo, [key]: value };
}

function updateSummaryField(key: string, value: string) {
snowflakeSummary = { ...snowflakeSummary, [key]: value };
}

$effect(() => {
loadData();
});
</script>

<AppShell title="Settings">
<div class="mx-auto flex max-w-2xl flex-col gap-6">

<!-- Tabs -->
<div class="flex gap-1 rounded-lg border p-1" style="border-color: var(--border)" role="tablist">
<button class="flex-1 rounded-md px-3 py-1.5 text-sm font-medium"
style="background: {activeTab === 'general' ? 'var(--accent)' : 'transparent'}; color: {activeTab === 'general' ? 'var(--accent-text)' : 'var(--text)'}"
onclick={() => activeTab = 'general'} role="tab" aria-selected={activeTab === 'general'}>
<BookOpen size={16} class="inline mr-1" />
General
</button>
<button class="flex-1 rounded-md px-3 py-1.5 text-sm font-medium"
style="background: {activeTab === 'summary' ? 'var(--accent)' : 'transparent'}; color: {activeTab === 'summary' ? 'var(--accent-text)' : 'var(--text)'}"
onclick={() => activeTab = 'summary'} role="tab" aria-selected={activeTab === 'summary'}>
<FileText size={16} class="inline mr-1" />
Summary
</button>
</div>

{#if !PROJECT_NAME}<NoProject />{:else if loading}
<p class="py-8 text-center" style="color: var(--muted)">Loading settings...</p>
{:else if error}
<p class="rounded-lg border p-4 text-sm" style="border-color: var(--danger); color: var(--danger)">{error}</p>
{:else}
<!-- General Tab -->
{#if activeTab === 'general'}
<section class="flex flex-col gap-4 rounded-lg border p-4" style="border-color: var(--border)">
<div class="flex items-center justify-between">
<div class="flex items-center gap-2">
<Palette size={20} />
<h2 class="text-lg font-semibold">Book Information</h2>
</div>
<button class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium"
style="background: var(--accent); color: var(--accent-text); opacity: {saving ? 0.7 : 1}"
onclick={saveInfo} disabled={saving}>
{#if saving}<span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />{:else if saved}<Check size={14} />{/if}
{saving ? 'Saving...' : 'Save'}
</button>
</div>

<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
{#each generalFields as field}
<div class="flex flex-col gap-1">
<label class="text-xs font-medium" style="color: var(--muted)">{field.label}</label>
<input class="rounded-lg border px-3 py-2 text-sm"
style="background: var(--surface); border-color: var(--border); color: var(--text)"
value={bookInfo[field.key] || ''}
oninput={(e) => updateField(field.key, (e.target as HTMLInputElement).value)}
placeholder={field.placeholder} />
</div>
{/each}
</div>
</section>

<!-- Summary Tab -->
{:else}
<section class="flex flex-col gap-4 rounded-lg border p-4" style="border-color: var(--border)">
<div class="flex items-center justify-between">
<div class="flex items-center gap-2">
<FileText size={20} />
<h2 class="text-lg font-semibold">Snowflake Summary</h2>
</div>
<button class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium"
style="background: var(--accent); color: var(--accent-text); opacity: {saving ? 0.7 : 1}"
onclick={saveSummary} disabled={saving}>
{#if saving}<span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />{:else if saved}<Check size={14} />{/if}
{saving ? 'Saving...' : 'Save'}
</button>
</div>

<div class="flex flex-col gap-4">
{#each summaryFields as field}
<div class="flex flex-col gap-1">
<label class="text-xs font-medium" style="color: var(--muted)">{field.label}</label>
<textarea class="w-full rounded-lg border px-3 py-2 text-sm"
rows={field.key === 'full' ? 6 : field.key === 'page' ? 4 : 2}
style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
value={snowflakeSummary[field.key] || ''}
oninput={(e) => updateSummaryField(field.key, (e.target as HTMLTextAreaElement).value)}
placeholder={field.placeholder} />
</div>
{/each}
</div>
</section>
{/if}
{/if}

<!-- App Settings -->
<section class="flex flex-col gap-4 rounded-lg border p-4" style="border-color: var(--border)">
<div class="flex items-center gap-2">
<Palette size={20} />
<h2 class="text-lg font-semibold">Appearance</h2>
</div>
<AppearanceSettings />
</section>

</div>
</AppShell>
