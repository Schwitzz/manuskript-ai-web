<script lang="ts">
	import AppShell from '#lib/components/AppShell.svelte';
	import NoProject from '#lib/components/NoProject.svelte';
	import { project } from '#lib/stores/project.svelte.ts';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import { Undo2, X } from '@lucide/svelte';
	import { call } from '#lib/api';
	import { addToast } from '#lib/stores/toast.svelte.ts';
	import { onMount } from 'svelte';

	const PROJECT = project.name ?? '';

	interface PlotStep {
		id: number;
		name: string;
		meta: string;
		summary: string;
	}

	interface Plot {
		id: number;
		name: string;
		importance: string;
		description: string;
		result: string;
		summary: string;
		characters: number[];
		steps: PlotStep[];
	}

	let plots: Plot[] = $state([]);
	let allChars: { id: number; name: string }[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let search = $state('');
	let selectedId: number | null = $state(null);
	let selected = $state<Plot | null>(null);
	let showForm = $state(false);
	let editingId: number | null = $state(null);
	let draft = $state<Plot | null>(null);
	let allDraft = $state<Plot | null>(null);
	let showStepForm = $state(false);
	let currentStep = $state<{ name: string; meta: string; summary: string }>({ name: '', meta: '', summary: '' });
	let editingStepId: number | null = $state(null);

	const importanceLabels = ['Minor', 'Supporting', 'Major'];

	function importanceBadge(level: string): string {
		return importanceLabels[parseInt(level) as 0 | 1 | 2] || 'Minor';
	}

	function importanceDot(level: string): string {
		const n = parseInt(level);
		return n >= 2 ? 'bg-red-500' : n === 1 ? 'bg-amber-500' : 'bg-gray-400';
	}

	function filtered() {
		if (!search.trim()) return plots;
		const q = search.toLowerCase();
		return plots.filter(p =>
			p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q)
		);
	}

	function selectPlot(id: number, plot: Plot) {
		selectedId = id;
		selected = { ...plot };
		editingId = id;
		allDraft = JSON.parse(JSON.stringify(plot));
		showForm = true;
	}

	function startNew() {
		editingId = null;
		allDraft = {
			id: 0, name: '', importance: '0', description: '', result: '', summary: '',
			characters: [], steps: []
		};
		showForm = true;
	}

	async function saveAll() {
		if (!allDraft || !allDraft.name.trim()) return;
		try {
			const payload = {
				name: allDraft.name,
				importance: allDraft.importance,
				description: allDraft.description,
				result: allDraft.result,
				summary: allDraft.summary,
				characters: allDraft.characters,
				steps: allDraft.steps.map(s => ({ name: s.name, meta: s.meta, summary: s.summary }))
			};
			if (editingId !== null) {
				const saved = await call('PUT /api/projects/{name}/plots/{plot_id}', {
					params: { name: PROJECT, plot_id: editingId },
					body: payload
				});
				const idx = plots.findIndex(p => p.id === editingId);
				if (idx !== -1) plots[idx] = saved as Plot;
				if (selectedId === editingId) { selected = { ...saved }; }
			} else {
				const saved = await call('POST /api/projects/{name}/plots', { params: { name: PROJECT }, body: payload } as any);
				plots.push(saved as Plot);
				editingId = saved.id;
				showForm = false;
			}
		} catch (e: any) { error = e.message; }
	}

	async function removePlot(p: Plot) {
		if (!confirm(`Delete "${p.name}"?`)) return;
		try {
			await call('DELETE /api/projects/{name}/plots/{plot_id}', {
				params: { name: PROJECT, plot_id: p.id }
			});
			plots = plots.filter(x => x.id !== p.id);
			if (selectedId === p.id) { selectedId = null; selected = null; }
			addToast(`"${p.name}" deleted`, {
				actionLabel: 'Undo',
				onAction: () => { restorePlot(p); }
			});
		} catch (e: any) { error = e.message; }
	}

	/** Undo a delete: the server really removed it, so create it again (it gets a new id). */
	async function restorePlot(original: Plot) {
		try {
			const saved = await call('POST /api/projects/{name}/plots', {
				params: { name: PROJECT },
				body: {
					name: original.name, importance: original.importance,
					description: original.description, result: original.result,
					summary: original.summary, characters: original.characters,
					steps: original.steps.map(s => ({ name: s.name, meta: s.meta, summary: s.summary }))
				}
			} as any);
			plots.push(saved as Plot);
		} catch (e: any) { error = e.message; }
	}

	function startAddStep() {
		editingStepId = null;
		currentStep = { name: '', meta: '', summary: '' };
		showStepForm = true;
	}

	function editStep(step: PlotStep) {
		editingStepId = step.id;
		currentStep = { name: step.name, meta: step.meta, summary: step.summary };
	}

	function saveStep() {
		if (!allDraft) return;
		if (editingStepId !== null) {
			const s = allDraft.steps.find(s => s.id === editingStepId);
			if (s) Object.assign(s, currentStep);
		} else {
			allDraft.steps.push({
				id: Date.now(), name: currentStep.name,
				meta: currentStep.meta, summary: currentStep.summary
			});
		}
		showStepForm = false;
		editingStepId = null;
	}

	function deleteStep(id: number) {
		if (!allDraft) return;
		allDraft.steps = allDraft.steps.filter(s => s.id !== id);
	}

	onMount(async () => {
	if (!PROJECT) { loading = false; return; }
		try {
			const [plotsData, charsData] = await Promise.all([
				call('GET /api/projects/{name}/plots', { params: { name: PROJECT } }),
				call('GET /api/projects/{name}/characters', { params: { name: PROJECT } })
			]);
			plots = (plotsData as any).plots ?? [];
			allChars = (charsData as any).characters ?? [];
		} catch (e: any) { error = e.message; }
		finally { loading = false; }
	});
</script>

<AppShell title="Plots">
	<div class="mx-auto flex max-w-2xl flex-col gap-4">
		{#if !PROJECT}<NoProject />{:else if loading}
			<p style="color: var(--muted)">Loading...</p>
		{:else if error}
			<p style="color: #ef4444">{error}</p>
		{:else if plots.length === 0}
			<EmptyState title="No plots yet">
				<button class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white"
					onclick={startNew}>Add first plot</button>
			</EmptyState>
		{:else}
			<div class="flex gap-2">
				<input class="flex-1 rounded-lg border px-3 py-2 text-sm"
					placeholder="Search plots..."
					style="background: var(--surface); border-color: var(--border); color: var(--text)"
					value={search}
					oninput={(e) => search = (e.target as HTMLInputElement).value} />
				<button class="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium"
					style="background: var(--accent); color: var(--accent-text)"
					onclick={startNew}>+ Add</button>
			</div>
			<div class="flex flex-col gap-2">
				{#each filtered() as p (p.id)}
					<div class="flex cursor-pointer items-center gap-3 rounded-lg border p-3"
						style="border-color: {selectedId === p.id ? 'var(--accent)' : 'var(--border)'}"
						onclick={() => selectPlot(p.id, p)}
							role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter') selectPlot(p.id, p); }}>
						<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
							style="background: {p.importance === '2' ? '#dc2626' : p.importance === '1' ? '#d97706' : '#6b7280'}">
							{importanceBadge(p.importance)}
						</div>
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2">
								<span class="font-medium truncate">{p.name}</span>
								<span class="inline-flex h-2 w-2 shrink-0 rounded-full {importanceDot(p.importance)}"
									title={importanceBadge(p.importance)}></span>
							</div>
							{#if p.description}
								<p class="truncate text-xs" style="color: var(--muted)">{p.description}</p>
							{/if}
							{#if p.steps.length > 0}
								<p class="text-xs" style="color: var(--muted)">{p.steps.length} step(s)</p>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{/if}

		{#if showForm && allDraft}
			<div class="flex flex-col gap-3 rounded-lg border p-4" style="border-color: var(--accent)">
				<div class="flex items-center justify-between">
					<h3 class="font-medium">{editingId !== null ? 'Edit' : 'New'} Plot</h3>
					<button class="rounded p-1" style="color: var(--muted)"
						onclick={() => { showForm = false; editingId = null; allDraft = null; }}>
						<X size={16}/></button>
				</div>
				<div class="grid grid-cols-2 gap-3">
					<div class="col-span-2 flex flex-col gap-1">
						<label class="text-xs" style="color: var(--muted)" for="plot-name">Name *</label>
						<input id="plot-name" class="rounded-lg border px-3 py-2 text-sm"
							style="background: var(--surface); border-color: var(--border); color: var(--text)"
							value={allDraft?.name}
							oninput={(e) => allDraft!.name = (e.target as HTMLInputElement).value}
							placeholder="Plot name" />
					</div>
					<div class="flex flex-col gap-1">
						<label class="text-xs" style="color: var(--muted)" for="plot-importance">Importance</label>
						<select id="plot-importance" class="rounded-lg border px-2 py-2 text-sm"
							style="background: var(--surface); border-color: var(--border)"
							value={allDraft?.importance}
							onchange={(e) => allDraft!.importance = (e.target as HTMLSelectElement).value}>
							<option value="0">{importanceBadge('0')}</option>
							<option value="1">{importanceBadge('1')}</option>
							<option value="2">{importanceBadge('2')}</option>
						</select>
					</div>
					<div class="flex flex-col gap-1">
						<label class="text-xs" style="color: var(--muted)" for="plot-characters">Characters</label>
						<select id="plot-characters" multiple class="rounded-lg border px-2 py-2 text-sm"
							style="background: var(--surface); border-color: var(--border)"
							onchange={(e) => {
								allDraft!.characters = Array.from((e.target as HTMLSelectElement).selectedOptions).map((o: HTMLOptionElement) => Number(o.value));
							}}>
							{#each allChars as c}
								<option value={c.id} selected={allDraft?.characters?.includes(c.id)}>{c.name}</option>
							{/each}
						</select>
					</div>
				</div>
				<div class="flex flex-col gap-1">
					<label class="text-xs" style="color: var(--muted)" for="plot-description">Description</label>
					<textarea id="plot-description" class="w-full rounded-lg border px-3 py-2 text-sm" rows={3}
						style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
						value={allDraft?.description}
						oninput={(e) => allDraft!.description = (e.target as HTMLTextAreaElement).value}
							placeholder="What is this plot about?"></textarea>
				</div>
				<div class="flex flex-col gap-1">
					<label class="text-xs" style="color: var(--muted)" for="plot-result">Result</label>
					<textarea id="plot-result" class="w-full rounded-lg border px-3 py-2 text-sm" rows={2}
						style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
						value={allDraft?.result}
						oninput={(e) => allDraft!.result = (e.target as HTMLTextAreaElement).value}
							placeholder="What results from this plot?"></textarea>
				</div>
				<div class="flex flex-col gap-1">
					<label class="text-xs" style="color: var(--muted)" for="plot-summary">Summary</label>
					<textarea id="plot-summary" class="w-full rounded-lg border px-3 py-2 text-sm" rows={2}
						style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
						value={allDraft?.summary}
						oninput={(e) => allDraft!.summary = (e.target as HTMLTextAreaElement).value}
							placeholder="Brief summary"></textarea>
				</div>
				<div class="flex flex-col gap-2">
					<div class="flex items-center justify-between">
						<label class="text-xs font-medium" style="color: var(--muted)" for="plot-steps">Resolution Steps</label>
						<button class="text-xs rounded px-2 py-1"
							style="background: var(--surface); border: 1px solid var(--border); color: var(--text)"
							onclick={startAddStep}>+ Add Step</button>
					</div>
					{#if allDraft.steps.length > 0}
						<div class="flex flex-col gap-1">
							{#each allDraft.steps as step (step.id)}
								<div class="flex items-center gap-2 rounded border px-3 py-2"
									style="border-color: var(--border)">
									<span class="flex-1 text-sm truncate">{step.name || 'Untitled'}</span>
									{#if step.summary}
										<span class="text-xs" style="color: var(--muted)">{step.summary.slice(0, 50)}{step.summary.length > 50 ? '...' : ''}</span>
									{/if}
									<button class="rounded px-1 text-xs" style="color: var(--muted)"
										onclick={() => editStep(step)}>Edit</button>
									<button class="rounded px-1 text-xs" style="color: #ef4444"
										onclick={() => deleteStep(step.id)}>X</button>
								</div>
							{/each}
						</div>
					{/if}
				</div>
				{#if showStepForm}
					<div class="rounded-lg border p-3" style="border-color: var(--border)">
						<h4 class="text-sm font-medium">
							{editingStepId !== null ? 'Edit Step' : 'New Step'}
						</h4>
						<div class="mt-2 flex flex-col gap-2">
							<input class="rounded border px-2 py-1 text-sm"
								style="background: var(--surface); border-color: var(--border); color: var(--text)"
								value={currentStep.name}
								oninput={(e) => currentStep.name = (e.target as HTMLInputElement).value}
								placeholder="Step name" />
							<input class="rounded border px-2 py-1 text-sm"
								style="background: var(--surface); border-color: var(--border); color: var(--text)"
								value={currentStep.meta}
								oninput={(e) => currentStep.meta = (e.target as HTMLInputElement).value}
								placeholder="Meta (optional)" />
							<textarea class="rounded border px-2 py-1 text-sm" rows={2}
								style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
								value={currentStep.summary}
								oninput={(e) => currentStep.summary = (e.target as HTMLTextAreaElement).value}
								placeholder="Summary"></textarea>
						</div>
						<div class="mt-2 flex gap-2">
							<button class="rounded px-3 py-1 text-sm" style="background: var(--accent); color: var(--accent-text)"
								onclick={saveStep}>Save</button>
							<button class="rounded px-3 py-1 text-sm"
								style="background: var(--surface); border-color: var(--border); color: var(--text)"
								onclick={() => { showStepForm = false; editingStepId = null; }}>Cancel</button>
						</div>
					</div>
				{/if}
				<div class="flex gap-2">
					<button class="flex-1 rounded-lg px-4 py-2 text-sm font-medium"
						style="background: var(--accent); color: var(--accent-text)"
						onclick={saveAll} disabled={!allDraft.name.trim()}>Save Plot</button>
					{#if editingId !== null}
						<button class="flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm"
							style="background: var(--surface); border-color: #ef4444; color: #ef4444"
							onclick={() => { if (confirm('Delete this plot?')) removePlot(selected!); }}>
							<Undo2 size={14}/> Delete
						</button>
					{/if}
				</div>
			</div>
		{/if}
	</div>
</AppShell>
