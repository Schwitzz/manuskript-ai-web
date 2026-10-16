<script lang="ts">
import AppShell from '#lib/components/AppShell.svelte';
import NoProject from '#lib/components/NoProject.svelte';
import ProjectNav from '#lib/components/ProjectNav.svelte';
import { project } from '#lib/stores/project.svelte.ts';
import EmptyState from '#lib/components/EmptyState.svelte';
import { Undo2, X, UserPlus } from '@lucide/svelte';
import { call } from '#lib/api';
import { addToast } from '#lib/stores/toast.svelte.ts';
import { onMount } from 'svelte';

const PROJECT = project.name ?? '';

interface Character {
id: number;
name: string;
importance: string;
pov: string;
motivation: string;
goal: string;
conflict: string;
epiphany: string;
summary_sentence: string;
summary_para: string;
summary_full: string;
notes: string;
color: string;
infos: [string, string][];
}

let characters: Character[] = $state([]);
let loading = $state(true);
let error = $state('');
let search = $state('');
let selectedId: number | null = $state(null);
let selected = $state<Character | null>(null);
let showForm = $state(false);
let editingId: number | null = $state(null);
let draft = $state<Character | null>(null);

const importanceLabels = ['Minor', 'Supporting', 'Major'];

function initials(name: string): string {
return name.split(/\s+/).map(w => w[0]).join('').toUpperCase().slice(0, 2);
}

function importanceBadge(level: string): string {
return importanceLabels[parseInt(level) as 0 | 1 | 2] || 'Minor';
}

function importanceDot(level: string): string {
const n = parseInt(level);
return n >= 2 ? 'bg-red-500' : n === 1 ? 'bg-amber-500' : 'bg-gray-400';
}

function filteredCharacters() {
if (!search.trim()) return characters;
const q = search.toLowerCase();
return characters.filter(c =>
c.name.toLowerCase().includes(q) ||
c.motivation.toLowerCase().includes(q) ||
c.goal.toLowerCase().includes(q)
);
}

function showInspector(id: number, c: Character) {
selectedId = id;
selected = { ...c };
editingId = id;
draft = { ...c };
showForm = true;
}

function startNew() {
editingId = null;
draft = {
id: 0, name: '', importance: '0', pov: '', motivation: '',
goal: '', conflict: '', epiphany: '', summary_sentence: '',
summary_para: '', summary_full: '', notes: '', color: '#3b82f6', infos: []
};
showForm = true;
}

async function save() {
if (!draft || !draft.name.trim()) return;
try {
if (editingId !== null) {
const saved = await call('PUT /api/projects/{name}/characters/{char_id}', {
params: { name: PROJECT, char_id: editingId },
body: draft
} as any);
const idx = characters.findIndex(c => c.id === editingId);
if (idx !== -1) characters[idx] = saved as Character;
if (selectedId === editingId) { selected = { ...saved }; }
} else {
const saved = await call('POST /api/projects/{name}/characters', {
params: { name: PROJECT },
body: draft
} as any);
characters.push(saved as Character);
editingId = saved.id;
showForm = false;
}
} catch (e: any) { error = e.message; }
}

async function removeChar(c: Character) {
if (!confirm(`Delete "${c.name}"?`)) return;
const charId = c.id;
const charName = c.name;
try {
await call('DELETE /api/projects/{name}/characters/{char_id}', {
params: { name: PROJECT, char_id: c.id }
});
characters = characters.filter(x => x.id !== charId);
if (selectedId === charId) { selectedId = null; selected = null; }
addToast(`"${charName}" deleted`, {
actionLabel: 'Undo',
onAction: () => { restoreChar(c); }
});
} catch (e: any) { error = e.message; }
}

/** Undo a delete: the server really removed it, so create it again (it gets a new id). */
async function restoreChar(original: Character): Promise<Character | null> {
try {
const { id: _gone, ...body } = original;
const saved = (await call('POST /api/projects/{name}/characters', { params: { name: PROJECT }, body } as any)) as Character;
characters.push(saved);
return saved;
} catch (e: any) {
error = e.message;
return null;
}
}

async function removeFormChar() {
if (editingId !== null) {
const charId = editingId;
const charName = draft?.name || '';
const original = characters.find(c => c.id === charId);
await call('DELETE /api/projects/{name}/characters/{char_id}', {
params: { name: PROJECT, char_id: editingId }
});
characters = characters.filter(c => c.id !== charId);
editingId = null;
showForm = false;
draft = null;
selected = null;
selectedId = null;
addToast(`"${charName}" deleted`, {
actionLabel: 'Undo',
onAction: async () => {
if (!original) return;
const back = await restoreChar(original);
if (back) {
showForm = true;
editingId = back.id;
draft = { ...back };
}
}
});
}
}

onMount(async () => {
if (!PROJECT) { loading = false; return; }
try {
const data = await call('GET /api/projects/{name}/characters', { params: { name: PROJECT } });
characters = (data as any).characters ?? [];
} catch (e: any) { error = e.message; }
finally { loading = false; }
});
</script>

<AppShell title="Characters">
<div class="mx-auto flex max-w-4xl flex-col gap-4">
	<ProjectNav active="characters" />
	{#if !PROJECT}<NoProject />{:else if loading}
		<p style="color: var(--muted)">Loading...</p>
	{:else if error}
		<p style="color: #ef4444">{error}</p>
	{:else if characters.length === 0}
		<EmptyState title="No characters yet">
			<button class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white"
				onclick={startNew}>Add first character</button>
		</EmptyState>
	{:else}
		<div class="flex gap-2">
			<input class="flex-1 rounded-lg border px-3 py-2 text-sm"
				placeholder="Search characters..."
				style="background: var(--surface); border-color: var(--border); color: var(--text)"
				value={search}
				oninput={(e) => search = (e.target as HTMLInputElement).value} />
			<button class="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium"
				style="background: var(--accent); color: var(--accent-text)"
				onclick={startNew}>+ Add</button>
		</div>
		<div class="flex flex-col gap-2">
			{#each filteredCharacters() as c (c.id)}
				<div class="flex cursor-pointer items-center gap-3 rounded-lg border p-3"
					style="border-color: {selectedId === c.id ? 'var(--accent)' : 'var(--border)'}"
					onclick={() => showInspector(c.id, c)}
					role="button"
					tabindex="0"
					onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); showInspector(c.id, c); } }}>
					<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
						style="background: {c.color}">{initials(c.name)}</div>
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2">
							<span class="font-medium truncate">{c.name}</span>
							<span class="inline-flex h-2 w-2 shrink-0 rounded-full {importanceDot(c.importance)}"
								title={importanceBadge(c.importance)}></span>
						</div>
						{#if c.motivation}
							<p class="truncate text-xs" style="color: var(--muted)">{c.motivation}</p>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
	{#if showForm && draft}
		<div class="flex flex-col gap-3 rounded-lg border p-4" style="border-color: var(--accent)">
			<div class="flex items-center justify-between">
				<h3 class="font-medium">{editingId !== null ? 'Edit' : 'New'} Character</h3>
				<button class="rounded p-1" style="color: var(--muted)"
					onclick={removeFormChar}><X size={16}/></button>
			</div>
			<div class="grid grid-cols-2 gap-3">
				<div class="col-span-2 flex flex-col gap-1">
					<label class="text-xs" style="color: var(--muted)" for="char-name">Name *</label>
					<input class="rounded-lg border px-3 py-2 text-sm"
						id="char-name"
						style="background: var(--surface); border-color: var(--border); color: var(--text)"
						value={draft!.name}
						oninput={(e) => draft!.name = (e.target as HTMLInputElement).value}
						placeholder="Character name" />
				</div>
				<div class="flex flex-col gap-1">
					<label class="text-xs" style="color: var(--muted)" for="char-importance">Importance</label>
					<select id="char-importance" class="rounded-lg border px-2 py-2 text-sm"
						style="background: var(--surface); border-color: var(--border)"
						value={draft!.importance}
						onchange={(e) => draft!.importance = (e.target as HTMLSelectElement).value}>
						<option value="0">{importanceBadge('0')}</option>
						<option value="1">{importanceBadge('1')}</option>
						<option value="2">{importanceBadge('2')}</option>
					</select>
				</div>
				<div class="flex flex-col gap-1">
					<label class="text-xs" style="color: var(--muted)" for="char-color">Color</label>
					<input id="char-color" class="h-10 w-full cursor-pointer rounded-lg border px-1"
						type="color"
						value={draft!.color}
						oninput={(e) => draft!.color = (e.target as HTMLInputElement).value} />
				</div>
			</div>

			{#each ['motivation','goal','conflict','epiphany'] as field}
				<div class="flex flex-col gap-1">
					<label class="text-xs" style="color: var(--muted)" for={`char-${field}`}>{field.charAt(0).toUpperCase() + field.slice(1)}</label>
					<textarea id={`char-${field}`} class="w-full rounded-lg border px-3 py-2 text-sm" rows={2}
						style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
						value={draft![field as keyof Character] as string}
						oninput={(e) => { const t = e.target as HTMLTextAreaElement; (draft! as any)[field] = t.value; }}
						placeholder={`Enter ${field}`}></textarea>
				</div>
			{/each}

			{#each ['summary_sentence','summary_para','summary_full'] as field}
				<div class="flex flex-col gap-1">
					<label class="text-xs" style="color: var(--muted)" for={`char-${field}`}>{field.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}</label>
					<textarea id={`char-${field}`} class="w-full rounded-lg border px-3 py-2 text-sm" rows={2}
						style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
						value={draft![field as keyof Character] as string}
						oninput={(e) => { const t = e.target as HTMLTextAreaElement; (draft! as any)[field] = t.value; }}
						placeholder={`Enter ${field}`}></textarea>
				</div>
			{/each}

			<div class="flex flex-col gap-1">
				<label class="text-xs" style="color: var(--muted)" for="char-notes">Notes</label>
				<textarea id="char-notes" class="w-full rounded-lg border px-3 py-2 text-sm" rows={2}
					style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
					value={draft!.notes}
					oninput={(e) => draft!.notes = (e.target as HTMLTextAreaElement).value}
					placeholder="Additional notes"></textarea>
			</div>

			<div class="flex gap-2">
				<button class="flex-1 rounded-lg px-4 py-2 text-sm font-medium"
					style="background: var(--accent); color: var(--accent-text)"
					onclick={save} disabled={!draft!.name.trim()}>Save</button>
				{#if editingId !== null}
					<button class="flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm"
						style="background: var(--surface); border-color: #ef4444; color: #ef4444"
						onclick={() => { if (confirm('Delete this character?')) removeChar(selected!); }}>
						<Undo2 size={14}/> Delete
					</button>
				{/if}
			</div>
		</div>
		{/if}
	</div>
</AppShell>