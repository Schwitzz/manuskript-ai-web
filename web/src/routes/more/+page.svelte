<script lang="ts">
import AppShell from '#lib/components/AppShell.svelte';
import AppearanceSettings from '#lib/components/AppearanceSettings.svelte';
import InstallPrompt from '#lib/components/InstallPrompt.svelte';
import TwoFactor from '#lib/components/TwoFactor.svelte';
import { auth } from '#lib/stores/auth.svelte.ts';
import { project, type ProjectItem } from '#lib/stores/project.svelte.ts';
import { LogOut, Brain, Settings2, Tag, UserPlus, FolderPlus, FolderOpen, Trash2, BookmarkPlus, LayoutTemplate } from '@lucide/svelte';
import { goto } from '$app/navigation';
import { call, ApiError } from '#lib/api.ts';
import { onMount } from 'svelte';

let projects = $state<ProjectItem[]>([]);
let creating = $state(false);
let newProjectName = $state('');
let newProjectTitle = $state('');
let newSample = $state('');
let samples = $state<string[]>([]);
let templates = $state<string[]>([]);
let newTemplate = $state('');
let savingFrom = $state<string | null>(null);
let templateName = $state('');
let templateKeepText = $state(false);
let savingTemplate = $state(false);
let error = $state('');

onMount(async () => {
await Promise.all([loadProjects(), loadTemplates()]);
try {
const data = await call('GET /api/projects/samples');
samples = data.samples;
} catch { /* no samples */ }
});

async function loadProjects() {
projects = await project.fetchProjects();
}

async function loadTemplates() {
try {
templates = (await call('GET /api/templates')).templates;
} catch { /* no templates */ }
}

function startSaveTemplate(p: ProjectItem) {
savingFrom = p.name;
templateName = p.title || p.name;
templateKeepText = false;
error = '';
}

async function handleSaveTemplate(e: SubmitEvent) {
e.preventDefault();
if (!savingFrom || !templateName.trim()) return;
savingTemplate = true;
error = '';
try {
await call('POST /api/templates', {
body: { name: templateName.trim(), from_project: savingFrom, keep_text: templateKeepText }
});
savingFrom = null;
await loadTemplates();
} catch (err: unknown) {
error = err instanceof ApiError ? err.message : 'Could not save template';
} finally {
savingTemplate = false;
}
}

async function handleDeleteTemplate(name: string) {
if (!confirm(`Delete template "${name}"? It is moved to the trash folder.`)) return;
try {
await call('DELETE /api/templates/{name}', { params: { name } });
if (newTemplate === name) newTemplate = '';
await loadTemplates();
} catch (err: unknown) {
error = err instanceof ApiError ? err.message : 'Could not delete template';
}
}

async function handleCreate(e: SubmitEvent) {
e.preventDefault();
error = '';
if (!newProjectName.trim()) {
error = 'Project name is required';
return;
}
creating = true;
try {
await call('POST /api/projects', {
body: {
name: newProjectName.trim(),
title: newProjectTitle.trim() || newProjectName.trim(),
sample: newSample || undefined,
template: newTemplate || undefined
}
});
newProjectName = '';
newProjectTitle = '';
newSample = '';
newTemplate = '';
await loadProjects();
} catch (err: unknown) {
error = err instanceof ApiError ? err.message : 'Could not create project';
} finally {
creating = false;
}
}

async function handleSelect(p: ProjectItem) {
project.select(p.name);
goto('/write');
}

async function handleDelete(name: string) {
if (!confirm(`Delete project "${name}"? This cannot be undone.`)) return;
try {
await call('DELETE /api/projects/{name}', { params: { name } });
if (project.name === name) {
project.select('');
}
await loadProjects();
} catch (err: unknown) {
error = err instanceof ApiError ? err.message : 'Could not delete project';
}
}
</script>

<AppShell title="More">
<div class="mx-auto flex max-w-xl flex-col gap-6">
<div>
<h2 class="mb-2 text-sm font-semibold">Projects</h2>
{#if projects.length === 0}
<p style="color: var(--muted); font-size: 0.875rem;">No projects yet. Create one below.</p>
{:else}
<ul class="mb-3 flex flex-col gap-1">
{#each projects as p (p.name)}
<li class="flex items-center gap-2">
<button
class="flex flex-1 items-center gap-3 rounded-lg border px-4 py-2"
style="background: {project.name === p.name ? 'var(--accent)' : 'var(--surface)'}; color: {project.name === p.name ? 'var(--accent-text)' : 'inherit'}; border-color: var(--border)"
onclick={() => handleSelect(p)}
>
<FolderOpen size={18} />
<span class="flex-1 truncate text-sm font-medium">{p.title || p.name}</span>
</button>
<button class="tap rounded p-2" style="color: var(--muted)" onclick={() => startSaveTemplate(p)} title="Save as template">
<BookmarkPlus size={16} />
</button>
<button class="tap rounded p-2" style="color: var(--danger)" onclick={() => handleDelete(p.name)} title="Delete project">
<Trash2 size={16} />
</button>
</li>
{/each}
</ul>
{/if}
{#if savingFrom}
<form onsubmit={handleSaveTemplate} class="mb-3 flex flex-col gap-3 rounded-lg border p-3" style="border-color: var(--accent)">
<h3 class="text-sm font-medium">Save "{savingFrom}" as a template</h3>
<label class="flex flex-col gap-1"><span class="text-xs">Template name</span>
<input class="rounded-lg border px-3 py-2 text-sm" style="background: var(--surface); border-color: var(--border)"
bind:value={templateName} autocomplete="off" maxlength="100" required />
</label>
<label class="flex items-center gap-2 text-sm">
<input type="checkbox" bind:checked={templateKeepText} />
Keep the written text (otherwise only the structure is saved)
</label>
{#if error}<p role="alert" style="color: var(--danger); font-size: 0.875rem;">{error}</p>{/if}
<div class="flex gap-2">
<button class="flex-1 rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-60"
style="background: var(--accent); color: var(--accent-text)" disabled={savingTemplate}>
{savingTemplate ? 'Saving...' : 'Save template'}
</button>
<button type="button" class="rounded-lg border px-4 py-2 text-sm" style="border-color: var(--border)"
onclick={() => (savingFrom = null)}>Cancel</button>
</div>
</form>
{/if}
</div>

{#if templates.length > 0}
<div>
<h2 class="mb-2 flex items-center gap-2 text-sm font-semibold"><LayoutTemplate size={16} /> Templates</h2>
<ul class="flex flex-col gap-1">
{#each templates as t (t)}
<li class="flex items-center gap-2 rounded-lg border px-4 py-2 text-sm" style="background: var(--surface); border-color: var(--border)">
<span class="flex-1 truncate">{t}</span>
<button class="tap rounded p-1" style="color: var(--danger)" onclick={() => handleDeleteTemplate(t)} title="Delete template">
<Trash2 size={16} />
</button>
</li>
{/each}
</ul>
</div>
{/if}

<div>
<h2 class="mb-2 flex items-center gap-2 text-sm font-semibold"><FolderPlus size={16} /> Create Project</h2>
<form onsubmit={handleCreate} class="flex flex-col gap-3">
<label class="flex flex-col gap-1"><span class="text-xs">Name</span>
<input class="rounded-lg border px-3 py-2 text-sm" style="background: var(--surface); border-color: var(--border)"
bind:value={newProjectName} autocomplete="off" placeholder="my-novel" required />
</label>
<label class="flex flex-col gap-1"><span class="text-xs">Title (optional)</span>
<input class="rounded-lg border px-3 py-2 text-sm" style="background: var(--surface); border-color: var(--border)"
bind:value={newProjectTitle} placeholder="My Novel" />
</label>
{#if templates.length > 0}
<label class="flex flex-col gap-1"><span class="text-xs">Start from a template</span>
<select class="rounded-lg border px-3 py-2 text-sm" style="background: var(--surface); border-color: var(--border)"
bind:value={newTemplate} onchange={() => { if (newTemplate) newSample = ''; }}>
<option value="">None (blank project)</option>
{#each templates as t}<option value={t}>{t}</option>{/each}
</select>
</label>
{/if}
{#if samples.length > 0}
<label class="flex flex-col gap-1"><span class="text-xs">Or start from a sample</span>
<select class="rounded-lg border px-3 py-2 text-sm" style="background: var(--surface); border-color: var(--border)"
bind:value={newSample} onchange={() => { if (newSample) newTemplate = ''; }}>
<option value="">None (blank project)</option>
{#each samples as s}<option value={s}>{s}</option>{/each}
</select>
</label>
{/if}
{#if error}<p role="alert" style="color: var(--danger); font-size: 0.875rem;">{error}</p>{/if}
<button class="rounded-lg px-4 py-2 font-medium disabled:opacity-60"
style="background: var(--accent); color: var(--accent-text)" disabled={creating}>
{creating ? 'Creating...' : 'Create Project'}
</button>
</form>
</div>

<button class="flex w-full items-center gap-3 rounded-lg border px-4"
style="background: var(--surface); border-color: var(--border)"
onclick={() => goto('/more/ai')}><Brain size={20} /> AI Settings</button>
<button class="flex w-full items-center gap-3 rounded-lg border px-4"
style="background: var(--surface); border-color: var(--border)"
onclick={() => goto('/labels')}><Tag size={20} /> Labels & Statuses</button>
<button class="flex w-full items-center gap-3 rounded-lg border px-4"
style="background: var(--surface); border-color: var(--border)"
onclick={() => goto('/register')}><UserPlus size={20} /> Create user</button>
<button class="flex w-full items-center gap-3 rounded-lg border px-4"
style="background: var(--surface); border-color: var(--border)"
onclick={() => goto('/settings')}><Settings2 size={20} /> App Settings</button>

<AppearanceSettings />
<TwoFactor />
<InstallPrompt />
<button class="flex w-full items-center gap-3 rounded-lg border px-4"
style="background: var(--surface); border-color: var(--border)"
onclick={() => auth.logout()}><LogOut size={20} /> Log out</button>
</div>
</AppShell>

