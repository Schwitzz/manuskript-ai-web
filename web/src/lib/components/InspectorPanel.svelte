<script lang="ts">
	import { call, ApiError } from '#lib/api';
	import { ChevronDown, ChevronUp } from '@lucide/svelte';
	import type { LabelDef, OutlineItem } from '#lib/outline.ts';

	let { scene, labels, statusList, project }: {
		scene: OutlineItem;
		labels: LabelDef[];
		statusList: string[];
		project: string;
	} = $props();

	type Field = 'label' | 'status' | 'summary_sentence' | 'goal' | 'pov' | 'notes';

	let open = $state(false);
	let error = $state('');
	let characters = $state<{ id: number; name: string }[]>([]);
	let draftSummary = $state('');
	let draftGoal = $state('');
	let draftNotes = $state('');

	// Re-sync the text drafts whenever the caller swaps in a different scene.
	$effect(() => {
		draftSummary = scene.summary_sentence;
		draftGoal = scene.goal;
		draftNotes = scene.notes;
		error = '';
	});

	// Characters are only needed for the POV picker, so fetch them when the panel is opened.
	$effect(() => {
		if (open && characters.length === 0) {
			call('GET /api/projects/{name}/characters', { params: { name: project } })
				.then((r) => (characters = r.characters.map((c) => ({ id: c.id, name: c.name }))))
				.catch(() => {});
		}
	});

	async function update(field: Field, value: string) {
		if (value === scene[field]) return;
		const before = scene[field];
		scene[field] = value; // optimistic; rolled back if the server refuses
		error = '';
		try {
			await call('PATCH /api/projects/{name}/outline/{item_id}/fields', {
				params: { name: project, item_id: scene.id },
				body: { [field]: value }
			});
		} catch (e) {
			scene[field] = before;
			error = e instanceof ApiError ? e.message : 'Could not save';
		}
	}
</script>

<div class="overflow-hidden rounded-lg border" style="border-color: var(--border)">
	<button
		class="flex w-full items-center justify-between px-4 py-3 text-sm font-medium"
		type="button"
		onclick={() => open = !open}
	>
		Inspector
		{#if open}<ChevronDown size={16} />{:else}<ChevronUp size={16} />{/if}
	</button>

	{#if open}
		<div class="flex flex-col gap-4 p-4" style="border-top: 1px solid var(--border)">
			{#if error}<p role="alert" class="text-xs" style="color: var(--danger)">{error}</p>{/if}
			<div class="flex flex-col gap-1">
				<label class="text-xs" style="color: var(--muted)">Label</label>
				<select
					class="w-full rounded border px-2 py-1.5 text-sm"
					style="background: var(--surface); border-color: var(--border)"
					value={scene.label}
					onchange={(e) => update('label', e.currentTarget.value)}
				>
					<option value="">None</option>
					{#each labels as l, i}
						<option value={String(i + 1)}>{l.name}</option>
					{/each}
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="text-xs" style="color: var(--muted)">Status</label>
				<select
					class="w-full rounded border px-2 py-1.5 text-sm"
					style="background: var(--surface); border-color: var(--border)"
					value={scene.status}
					onchange={(e) => update('status', e.currentTarget.value)}
				>
					<option value="">None</option>
					{#each statusList as s, i}
						<option value={String(i + 1)}>{s}</option>
					{/each}
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="text-xs" style="color: var(--muted)">Summary</label>
				<textarea
					class="w-full rounded border px-2 py-1.5 text-sm"
					rows={2}
					style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
					value={draftSummary}
					oninput={(e) => draftSummary = (e.target as HTMLTextAreaElement).value}
					onblur={() => update('summary_sentence', draftSummary)}
					placeholder="One-sentence summary"
				/>
			</div>

			<div class="flex flex-col gap-1">
				<label class="text-xs" style="color: var(--muted)">Goal</label>
				<textarea
					class="w-full rounded border px-2 py-1.5 text-sm"
					rows={2}
					style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
					value={draftGoal}
					oninput={(e) => draftGoal = (e.target as HTMLTextAreaElement).value}
					onblur={() => update('goal', draftGoal)}
					placeholder="What this scene needs to achieve"
				/>
			</div>

			<div class="flex flex-col gap-1">
				<label class="text-xs" style="color: var(--muted)">POV</label>
				<select
					class="w-full rounded border px-2 py-1.5 text-sm"
					style="background: var(--surface); border-color: var(--border); color: var(--text)"
					value={scene.pov}
					onchange={(e) => update('pov', e.currentTarget.value)}
				>
					<option value="">None</option>
					{#each characters as c}
						<option value={String(c.id)}>{c.name}</option>
					{/each}
					{#if scene.pov && !characters.some((c) => String(c.id) === scene.pov)}
						<option value={scene.pov}>Character #{scene.pov}</option>
					{/if}
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="text-xs" style="color: var(--muted)">Notes</label>
				<textarea
					class="w-full rounded border px-2 py-1.5 text-sm"
					rows={3}
					style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
					value={draftNotes}
					oninput={(e) => draftNotes = (e.target as HTMLTextAreaElement).value}
					onblur={() => update('notes', draftNotes)}
					placeholder="Scene notes"
				/>
			</div>
		</div>
	{/if}
</div>
