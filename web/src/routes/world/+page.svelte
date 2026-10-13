<script lang="ts">
import AppShell from '#lib/components/AppShell.svelte';
import NoProject from '#lib/components/NoProject.svelte';
import { project } from '#lib/stores/project.svelte.ts';
import EmptyState from '#lib/components/EmptyState.svelte';
import { ChevronRight, Plus, Trash2, X } from '@lucide/svelte';
import { call } from '#lib/api';
import { addToast } from '#lib/stores/toast.svelte.ts';
import { onMount } from 'svelte';

const PROJECT = project.name ?? '';

interface WorldItem {
id: number;
name: string;
description: string;
passion: string;
conflict: string;
children: WorldItem[];
}

let items: WorldItem[] = $state([]);
let loading = $state(true);
let error = $state('');
let expanded = $state(new Set<number>());
let editingId: number | null = $state(null);
let draft = $state<{ name: string; description: string; passion: string; conflict: string; parentId: number | null } | null>(null);
let showForm = $state(false);
let formMode = $state('create' as 'create' | 'edit');
let parentIdOfForm: number | null = $state(null);

function toggle(id: number) {
if (expanded.has(id)) expanded.delete(id);
else expanded.add(id);
}

function flattenItems(list: WorldItem[]): (WorldItem & { depth: number; parentId: number | null })[] {
const result: (WorldItem & { depth: number; parentId: number | null })[] = [];
for (const item of list) {
result.push({ ...item, depth: 0, parentId: null });
if (expanded.has(item.id) && item.children.length > 0) {
for (const child of flattenItems(item.children)) {
result.push({ ...child, depth: child.depth + 1, parentId: item.id });
}
}
}
return result;
}

function findItemById(list: WorldItem[], id: number): WorldItem | null {
for (const item of list) {
if (item.id === id) return item;
const found = findItemById(item.children, id);
if (found) return found;
}
return null;
}

function startAdd(parentId: number | null = null) {
formMode = 'create';
parentIdOfForm = parentId;
draft = { name: '', description: '', passion: '', conflict: '', parentId };
showForm = true;
editingId = null;
}

function startEdit(item: WorldItem) {
formMode = 'edit';
draft = { name: item.name, description: item.description, passion: item.passion, conflict: item.conflict, parentId: null };
showForm = true;
editingId = item.id;
}

async function saveForm() {
if (!draft || !draft.name.trim()) return;
try {
if (formMode === 'edit' && editingId !== null) {
const saved = await call('PATCH /api/projects/{name}/world/{item_id}', {
params: { name: PROJECT, item_id: editingId },
body: { name: draft.name, description: draft.description, passion: draft.passion, conflict: draft.conflict }
});
const updated = saved as any;
// Replace item in tree
const flat = flattenItems(items);
const found = findItemById(items, editingId);
if (found) {
found.name = updated.name;
found.description = updated.description;
found.passion = updated.passion;
found.conflict = updated.conflict;
}
} else {
const saved = await call('POST /api/projects/{name}/world', {
params: { name: PROJECT },
body: { name: draft.name, description: draft.description || undefined, passion: draft.passion || undefined, conflict: draft.conflict || undefined, parent_id: draft.parentId }
} as any);
const newItem = saved as any;
if (draft.parentId !== null) {
const parent = findItemById(items, draft.parentId);
if (parent) {
parent.children.push(newItem);
expanded.add(draft.parentId);
}
} else {
items.push(newItem);
}
}
showForm = false;
draft = null;
editingId = null;
} catch (e: any) { error = e.message; }
}

function findParentList(list: WorldItem[], id: number): WorldItem[] | null {
if (list.some(x => x.id === id)) return list;
for (const item of list) {
const found = findParentList(item.children, id);
if (found) return found;
}
return null;
}

async function removeItem(item: WorldItem) {
if (!confirm(`Delete "${item.name}"?`)) return;
try {
await call('DELETE /api/projects/{name}/world/{item_id}', {
params: { name: PROJECT, item_id: item.id }
});
const parentList = findParentList(items, item.id) ?? items;
const parentId = parentList === items ? null : (flattenItems(items).find(x => x.children === parentList)?.id ?? null);
const idx = parentList.findIndex(x => x.id === item.id);
if (idx !== -1) parentList.splice(idx, 1);
addToast(`"${item.name}" deleted`, {
actionLabel: 'Undo',
onAction: () => { restoreItem(item, parentId); }
});
} catch (e: any) { error = e.message; }
}

/** Undo a delete: the server removed the item and everything under it, so create them again. */
async function restoreItem(original: WorldItem, parentId: number | null) {
try {
const saved = (await call('POST /api/projects/{name}/world', {
params: { name: PROJECT },
body: {
name: original.name, description: original.description || undefined,
passion: original.passion || undefined, conflict: original.conflict || undefined,
parent_id: parentId
}
} as any)) as WorldItem;
saved.children = [];
const list = parentId === null ? items : findItemById(items, parentId)?.children;
if (!list) { await reloadWorld(); return; }
list.push(saved);
for (const child of original.children) await restoreItem(child, saved.id);
} catch (e: any) { error = e.message; }
}

async function reloadWorld() {
const data = await call('GET /api/projects/{name}/world', { params: { name: PROJECT } });
items = data.items as WorldItem[];
}

onMount(async () => {
if (!PROJECT) { loading = false; return; }
try {
const data = await call('GET /api/projects/{name}/world', { params: { name: PROJECT } });
items = (data as any).items ?? [];
} catch (e: any) { error = e.message; }
finally { loading = false; }
});
</script>

<AppShell title="World">
<div class="mx-auto flex max-w-2xl flex-col gap-4">
{#if !PROJECT}<NoProject />{:else if loading}
<p style="color: var(--muted)">Loading...</p>
{:else if error}
<p style="color: #ef4444">{error}</p>
{:else if items.length === 0}
<EmptyState title="No world items yet">
<button class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white"
onclick={() => startAdd()}>Add first item</button>
</EmptyState>
{:else}
<div class="flex gap-2">
<button class="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium"
style="background: var(--accent); color: var(--accent-text)"
onclick={() => startAdd()}>+ Add Root</button>
</div>
<div class="flex flex-col gap-1">
{#each flattenItems(items) as item (item.id)}
<div class="flex items-center gap-2 rounded-lg border p-2 px-3"
style="border-color: var(--border); margin-left: {item.depth * 24}px">
{#if item.children.length > 0}
<button class="rounded p-0.5" style="color: var(--muted)"
onclick={() => toggle(item.id)}>
<ChevronRight size={14} style="transform: {expanded.has(item.id) ? 'rotate(90deg)' : 'none'}"/>
</button>
{:else}
<span class="w-4"></span>
{/if}
<span class="flex-1 text-sm truncate">{item.name}</span>
<button class="rounded p-1 text-xs" style="color: var(--muted)"
onclick={() => startEdit(item)}>Edit</button>
<button class="rounded p-1 text-xs" style="color: #ef4444"
onclick={() => removeItem(item)}>Del</button>
<button class="rounded p-1 text-xs" style="color: var(--muted)"
onclick={() => startAdd(item.id)}>+</button>
</div>
{/each}
</div>
{/if}
{#if showForm && draft}
<div class="flex flex-col gap-3 rounded-lg border p-4" style="border-color: var(--accent)">
<div class="flex items-center justify-between">
<h3 class="font-medium">{formMode === 'edit' ? 'Edit' : 'New'} World Item</h3>
<button class="rounded p-1" style="color: var(--muted)"
onclick={() => { showForm = false; draft = null; editingId = null; }}>
<X size={16}/></button>
</div>
{#if formMode === 'create' && parentIdOfForm !== null}
<p class="text-xs" style="color: var(--muted)">Child of: {findItemById(items, parentIdOfForm)?.name}</p>
{/if}
<div class="flex flex-col gap-1">
<label for="name" class="text-xs" style="color: var(--muted)">Name *</label>
<input id="name" class="rounded-lg border px-3 py-2 text-sm"
style="background: var(--surface); border-color: var(--border); color: var(--text)"
value={draft?.name}
oninput={(e) => draft!.name = (e.target as HTMLInputElement).value}
placeholder="Item name" />
</div>
<div class="flex flex-col gap-1">
<label class="text-xs" style="color: var(--muted)" for="world-description">Description</label>
<textarea id="world-description" class="w-full rounded-lg border px-3 py-2 text-sm" rows={2}
style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
value={draft?.description}
oninput={(e) => draft!.description = (e.target as HTMLTextAreaElement).value}
placeholder="What is this?"></textarea>
</div>
<div class="flex flex-col gap-1">
<label class="text-xs" style="color: var(--muted)" for="world-passion">Passion</label>
<textarea id="world-passion" class="w-full rounded-lg border px-3 py-2 text-sm" rows={2}
style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
value={draft?.passion}
oninput={(e) => draft!.passion = (e.target as HTMLTextAreaElement).value}
placeholder="What do they love?"></textarea>
</div>
<div class="flex flex-col gap-1">
<label class="text-xs" style="color: var(--muted)" for="world-conflict">Conflict</label>
<textarea id="world-conflict" class="w-full rounded-lg border px-3 py-2 text-sm" rows={2}
style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
value={draft?.conflict}
oninput={(e) => draft!.conflict = (e.target as HTMLTextAreaElement).value}
placeholder="What opposes them?"></textarea>
</div>
<div class="flex gap-2">
<button class="flex-1 rounded-lg px-4 py-2 text-sm font-medium"
style="background: var(--accent); color: var(--accent-text)"
onclick={saveForm} disabled={!draft.name.trim()}>Save</button>
<button class="rounded-lg border px-4 py-2 text-sm"
style="background: var(--surface); border-color: var(--border); color: var(--text)"
onclick={() => { showForm = false; draft = null; editingId = null; }}>Cancel</button>
</div>
</div>
{/if}
</div>
</AppShell>
