<script lang="ts">
import AppShell from '#lib/components/AppShell.svelte';
import NoProject from '#lib/components/NoProject.svelte';
import ProjectNav from '#lib/components/ProjectNav.svelte';
import { project } from '#lib/stores/project.svelte.ts';
import { Palette, Plus, Trash2, X, Check } from '@lucide/svelte';
import { call } from '#lib/api';
import { addToast } from '#lib/stores/toast.svelte.ts';
import { goto } from '$app/navigation';

const PROJECT_NAME = project.name ?? '';

let labels = $state<{ name: string; color: string }[]>([]);
let statusList = $state<string[]>([]);
let loading = $state(true);
let error = $state('');

let saving = $state(false);
let saved = $state(true);

// Label editing
let newLabelName = $state('');
let newLabelColor = $state('#3b82f6');
let editingLabelIdx = $state<number | null>(null);
let editingLabelName = $state('');
let editingLabelColor = $state('');

// Status editing
let newStatusName = $state('');
let editingStatusIdx = $state<number | null>(null);
let editingStatusName = $state('');

async function loadData() {
if (!PROJECT_NAME) { loading = false; return; }
try {
loading = true;
error = '';
const data = await call('GET /api/projects/{name}/labels', {
params: { name: PROJECT_NAME }
});
labels = (data as any).labels || [];
statusList = (data as any).status || [];
loading = false;
} catch (e: any) {
error = e.message || 'Failed to load labels';
loading = false;
}
}

async function saveLabels() {
try {
saving = true;
saved = false;
await call('PUT /api/projects/{name}/labels', {
params: { name: PROJECT_NAME },
body: { labels }
});
saved = true;
setTimeout(() => { saved = true; }, 2000);
} catch (e: any) {
error = e.message;
} finally {
saving = false;
}
}

async function saveStatus() {
try {
saving = true;
saved = false;
await call('PUT /api/projects/{name}/status', {
params: { name: PROJECT_NAME },
body: { status: statusList }
});
saved = true;
setTimeout(() => { saved = true; }, 2000);
} catch (e: any) {
error = e.message;
} finally {
saving = false;
}
}

function addLabel() {
const name = newLabelName.trim();
if (!name) return;
if (labels.some(l => l.name.toLowerCase() === name.toLowerCase())) {
error = 'Label already exists';
return;
}
labels = [...labels, { name, color: newLabelColor }];
newLabelName = '';
newLabelColor = '#3b82f6';
}

function startEditLabel(idx: number) {
editingLabelIdx = idx;
editingLabelName = labels[idx].name;
editingLabelColor = labels[idx].color;
}

function cancelEditLabel() {
editingLabelIdx = null;
editingLabelName = '';
editingLabelColor = '';
}

function saveEditLabel(idx: number) {
const name = editingLabelName.trim();
if (!name) return;
if (labels.some((l, i) => i !== idx && l.name.toLowerCase() === name.toLowerCase())) {
error = 'Label name already exists';
return;
}
labels = labels.map((l, i) => i === idx ? { name, color: editingLabelColor } : l);
editingLabelIdx = null;
}

function deleteLabel(idx: number) {
const label = labels[idx];
const labelName = label.name;
const labelId = `label-${labelName}`;
labels = labels.filter((_, i) => i !== idx);
addToast(`"${labelName}" deleted`, {
actionLabel: 'Undo',
onAction: () => {
labels.splice(idx, 0, { name: labelName, color: label.color });
}
});
}

function addStatus() {
const name = newStatusName.trim();
if (!name || statusList.includes(name)) return;
statusList = [...statusList, name];
newStatusName = '';
}

function startEditStatus(idx: number) {
editingStatusIdx = idx;
editingStatusName = statusList[idx];
}

function cancelEditStatus() {
editingStatusIdx = null;
editingStatusName = '';
}

function saveEditStatus(idx: number) {
const name = editingStatusName.trim();
if (!name || statusList.some((s, i) => i !== idx && s === name)) return;
statusList = statusList.map((s, i) => i === idx ? name : s);
editingStatusIdx = null;
}

function deleteStatus(idx: number) {
const statusName = statusList[idx];
statusList = statusList.filter((_, i) => i !== idx);
addToast(`"${statusName}" deleted`, {
actionLabel: 'Undo',
onAction: () => {
statusList.splice(idx, 0, statusName);
}
});
}

$effect(() => {
loadData();
});
</script>

<AppShell title="Labels & Statuses">
<div class="mx-auto flex max-w-4xl flex-col gap-6">
<ProjectNav active="labels" />

{#if !PROJECT_NAME}<NoProject />{:else if loading}
<p class="py-8 text-center" style="color: var(--muted)">Loading...</p>
{:else if error}
<p class="rounded-lg border p-4 text-sm" style="border-color: var(--danger); color: var(--danger)">{error}</p>
{/if}

<!-- Labels Section -->
<section class="flex flex-col gap-4 rounded-lg border p-4" style="border-color: var(--border)">
<div class="flex items-center justify-between">
<div class="flex items-center gap-2">
<Palette size={20} />
<h2 class="text-lg font-semibold">Labels</h2>
</div>
<button class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium"
style="background: var(--accent); color: var(--accent-text); opacity: {saving ? 0.7 : 1}"
onclick={saveLabels} disabled={saving}>
{#if saving}<span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"></span>{:else if saved}<Check size={14} />{/if}
{saving ? 'Saving...' : 'Save'}
</button>
</div>

<!-- Add label -->
<div class="flex gap-2">
<input class="flex-1 rounded-lg border px-3 py-2 text-sm"
style="background: var(--surface); border-color: var(--border); color: var(--text)"
value={newLabelName}
oninput={(e) => newLabelName = (e.target as HTMLInputElement).value}
placeholder="New label name" />
<input class="h-10 w-14 cursor-pointer rounded-lg border"
type="color"
value={newLabelColor}
oninput={(e) => newLabelColor = (e.target as HTMLInputElement).value} />
<button class="rounded-lg px-3 py-2 text-sm font-medium"
style="background: var(--accent); color: var(--accent-text)"
onclick={addLabel}>+</button>
</div>

<!-- Label list -->
{#if labels.length > 0}
<div class="flex flex-col gap-2">
{#each labels as label, idx}
<div class="flex items-center gap-2 rounded-lg border px-3 py-2"
style="border-color: var(--border)">
{#if editingLabelIdx === idx}
<input class="flex-1 rounded border px-2 py-1 text-sm"
style="background: var(--surface); border-color: var(--border); color: var(--text)"
value={editingLabelName}
oninput={(e) => editingLabelName = (e.target as HTMLInputElement).value}
onkeydown={(e) => { if (e.key === 'Enter') saveEditLabel(idx); if (e.key === 'Escape') cancelEditLabel(); }}
/>
<input class="h-8 w-12 cursor-pointer rounded border"
type="color"
value={editingLabelColor}
oninput={(e) => editingLabelColor = (e.target as HTMLInputElement).value} />
<button class="rounded p-1 text-sm" style="color: var(--success)"
onclick={() => saveEditLabel(idx)}><Check size={16}/></button>
<button class="rounded p-1 text-sm" style="color: var(--muted)"
onclick={cancelEditLabel}><X size={16}/></button>
{:else}
<div class="h-4 w-4 rounded-full"
style="background-color: {label.color}"></div>
<span class="flex-1 text-sm">{label.name}</span>
<button class="rounded p-1 text-sm" style="color: var(--muted)"
onclick={() => startEditLabel(idx)}><Palette size={14}/></button>
<button class="rounded p-1 text-sm" style="color: #ef4444"
onclick={() => deleteLabel(idx)}><Trash2 size={14}/></button>
{/if}
</div>
{/each}
</div>
{/if}
</section>

<!-- Status Section -->
<section class="flex flex-col gap-4 rounded-lg border p-4" style="border-color: var(--border)">
<div class="flex items-center justify-between">
<div class="flex items-center gap-2">
<Palette size={20} />
<h2 class="text-lg font-semibold">Statuses</h2>
</div>
<button class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium"
style="background: var(--accent); color: var(--accent-text); opacity: {saving ? 0.7 : 1}"
onclick={saveStatus} disabled={saving}>
{#if saving}<span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"></span>{:else if saved}<Check size={14} />{/if}
{saving ? 'Saving...' : 'Save'}
</button>
</div>

<!-- Add status -->
<div class="flex gap-2">
<input class="flex-1 rounded-lg border px-3 py-2 text-sm"
style="background: var(--surface); border-color: var(--border); color: var(--text)"
value={newStatusName}
oninput={(e) => newStatusName = (e.target as HTMLInputElement).value}
placeholder="New status" />
<button class="rounded-lg px-3 py-2 text-sm font-medium"
style="background: var(--accent); color: var(--accent-text)"
onclick={addStatus}>+</button>
</div>

<!-- Status list -->
{#if statusList.length > 0}
<div class="flex flex-col gap-2">
{#each statusList as status, idx}
<div class="flex items-center gap-2 rounded-lg border px-3 py-2"
style="border-color: var(--border)">
{#if editingStatusIdx === idx}
<input class="flex-1 rounded border px-2 py-1 text-sm"
style="background: var(--surface); border-color: var(--border); color: var(--text)"
value={editingStatusName}
oninput={(e) => editingStatusName = (e.target as HTMLInputElement).value}
onkeydown={(e) => { if (e.key === 'Enter') saveEditStatus(idx); if (e.key === 'Escape') cancelEditStatus(); }}
/>
<button class="rounded p-1 text-sm" style="color: var(--success)"
onclick={() => saveEditStatus(idx)}><Check size={16}/></button>
<button class="rounded p-1 text-sm" style="color: var(--muted)"
onclick={cancelEditStatus}><X size={16}/></button>
{:else}
<span class="flex-1 text-sm">{status}</span>
<button class="rounded p-1 text-sm" style="color: var(--muted)"
onclick={() => startEditStatus(idx)}><Palette size={14}/></button>
<button class="rounded p-1 text-sm" style="color: #ef4444"
onclick={() => deleteStatus(idx)}><Trash2 size={14}/></button>
{/if}
</div>
{/each}
</div>
{/if}
</section>

</div>
</AppShell>
