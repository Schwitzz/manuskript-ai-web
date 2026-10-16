<script lang="ts">
	import AppShell from '#lib/components/AppShell.svelte';
	import NoProject from '#lib/components/NoProject.svelte';
	import ProjectNav from '#lib/components/ProjectNav.svelte';
	import { project } from '#lib/stores/project.svelte.ts';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import {
		Plus, Trash2, Search, GitBranch, Check, ArrowUp, ArrowDown, Users, Sparkles
	} from '@lucide/svelte';
	import { call } from '#lib/api';
	import { addToast } from '#lib/stores/toast.svelte.ts';
	import { onMount } from 'svelte';

	const PROJECT = $derived(project.name ?? '');

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

	// Desktop Manuskript's Plot Step Stage presets (`plotDelegate.py`)
	const STEP_STAGE_GROUPS: { group: string; stages: string[] }[] = [
		{ group: 'General', stages: ['Promise', 'Problem', 'Progress', 'Resolution'] },
		{ group: 'Try / Fail', stages: ['No and', 'Yes but'] },
		{ group: "Freytag's Pyramid", stages: ['Exposition', 'Rising action', 'Climax', 'Falling action', 'Resolution'] },
		{
			group: 'Three Acts',
			stages: [
				'1. Setup', '1. Inciting event', '1. Turning point',
				'2. Choice', '2. Reversal', '2. Disaster',
				'3. Stand up', '3. Climax', '3. Ending'
			]
		},
		{
			group: "Hero's Journey",
			stages: [
				'Ordinary world', 'Call to adventure', 'Refusal of the call',
				'Meeting with mentor', 'Crossing the Threshold', 'Tests',
				'Approach', 'Abyss', 'Reward / Revelation', 'Transformation',
				'Atonement', 'Return'
			]
		},
		{
			group: 'Dan Wells 7-Point',
			stages: ['Hook', 'Plot Turn 1', 'Pinch 1', 'Midpoint', 'Pinch 2', 'Plot Turn 2', 'Resolution']
		}
	];

	let plots: Plot[] = $state([]);
	let allChars: { id: number; name: string; color?: string }[] = $state([]);
	let loading = $state(true);
	let saving = $state(false);
	let saved = $state(true);
	let error = $state('');
	let search = $state('');
	let selectedId: number | null = $state(null);
	let activePlotTab = $state<'infos' | 'steps'>('infos');
	let selectedStepIdx = $state<number | null>(null);
	let draft = $state<Plot | null>(null);

	const importanceLabels = ['Minor', 'Secondary', 'Main'];

	function importanceBadge(level: string): string {
		return importanceLabels[parseInt(level) as 0 | 1 | 2] || 'Minor';
	}

	function filtered() {
		if (!search.trim()) return plots;
		const q = search.toLowerCase();
		return plots.filter(
			(p) => p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q)
		);
	}

	function selectPlot(plot: Plot) {
		selectedId = plot.id;
		draft = JSON.parse(JSON.stringify(plot));
		selectedStepIdx = draft && draft.steps.length > 0 ? 0 : null;
		saved = true;
	}

	async function createNewPlot() {
		try {
			const created = (await call('POST /api/projects/{name}/plots', {
				params: { name: PROJECT },
				body: {
					name: `Plot ${plots.length + 1}`,
					importance: '2',
					description: '',
					result: '',
					summary: '',
					characters: [],
					steps: []
				}
			} as any)) as Plot;
			plots = [...plots, created];
			selectPlot(created);
		} catch (e: any) {
			error = e.message;
		}
	}

	async function saveDraft() {
		if (!draft || selectedId === null || !draft.name.trim()) return;
		saving = true;
		saved = false;
		try {
			const payload = {
				name: draft.name.trim(),
				importance: draft.importance,
				description: draft.description,
				result: draft.result,
				summary: draft.summary,
				characters: draft.characters,
				steps: draft.steps.map((s) => ({
					name: s.name || 'Step',
					meta: s.meta || '',
					summary: s.summary || ''
				}))
			};
			const updated = (await call('PUT /api/projects/{name}/plots/{plot_id}', {
				params: { name: PROJECT, plot_id: selectedId },
				body: payload
			})) as Plot;
			plots = plots.map((p) => (p.id === selectedId ? updated : p));
			draft = JSON.parse(JSON.stringify(updated));
			saved = true;
		} catch (e: any) {
			error = e.message;
		} finally {
			saving = false;
		}
	}

	function toggleCharacterLink(charId: number) {
		if (!draft) return;
		if (draft.characters.includes(charId)) {
			draft.characters = draft.characters.filter((id) => id !== charId);
		} else {
			draft.characters = [...draft.characters, charId];
		}
		saved = false;
	}

	function addStep(name = 'New step', meta = '') {
		if (!draft) return;
		const nextStep: PlotStep = {
			id: Date.now() + Math.floor(Math.random() * 1000),
			name,
			meta,
			summary: ''
		};
		draft.steps = [...draft.steps, nextStep];
		selectedStepIdx = draft.steps.length - 1;
		saved = false;
	}

	function insertStageTemplate(groupName: string) {
		if (!draft) return;
		const grp = STEP_STAGE_GROUPS.find((g) => g.group === groupName);
		if (!grp) return;
		const added = grp.stages.map((st, idx) => ({
			id: Date.now() + idx,
			name: st,
			meta: st,
			summary: ''
		}));
		draft.steps = [...draft.steps, ...added];
		selectedStepIdx = draft.steps.length - 1;
		saved = false;
	}

	function moveStep(idx: number, delta: -1 | 1) {
		if (!draft) return;
		const target = idx + delta;
		if (target < 0 || target >= draft.steps.length) return;
		const copy = [...draft.steps];
		const [moved] = copy.splice(idx, 1);
		copy.splice(target, 0, moved);
		draft.steps = copy;
		selectedStepIdx = target;
		saved = false;
	}

	function removeStep(idx: number) {
		if (!draft) return;
		draft.steps = draft.steps.filter((_, i) => i !== idx);
		if (selectedStepIdx === idx) {
			selectedStepIdx = draft.steps.length > 0 ? 0 : null;
		}
		saved = false;
	}

	async function removePlot(p: Plot) {
		if (!confirm(`Delete "${p.name}"?`)) return;
		try {
			await call('DELETE /api/projects/{name}/plots/{plot_id}', {
				params: { name: PROJECT, plot_id: p.id }
			});
			plots = plots.filter((x) => x.id !== p.id);
			if (selectedId === p.id) {
				if (plots[0]) selectPlot(plots[0]);
				else {
					selectedId = null;
					draft = null;
				}
			}
			addToast(`"${p.name}" deleted`, {
				actionLabel: 'Undo',
				onAction: () => {
					void restorePlot(p);
				}
			});
		} catch (e: any) {
			error = e.message;
		}
	}

	async function restorePlot(original: Plot) {
		try {
			const s = (await call('POST /api/projects/{name}/plots', {
				params: { name: PROJECT },
				body: {
					name: original.name,
					importance: original.importance,
					description: original.description,
					result: original.result,
					summary: original.summary,
					characters: original.characters,
					steps: original.steps.map((st) => ({
						name: st.name,
						meta: st.meta,
						summary: st.summary
					}))
				}
			} as any)) as Plot;
			plots = [...plots, s];
			selectPlot(s);
		} catch (e: any) {
			error = e.message;
		}
	}

	onMount(async () => {
		if (!PROJECT) {
			loading = false;
			return;
		}
		try {
			const [plotsData, charsData] = await Promise.all([
				call('GET /api/projects/{name}/plots', { params: { name: PROJECT } }),
				call('GET /api/projects/{name}/characters', { params: { name: PROJECT } })
			]);
			plots = (plotsData as any).plots ?? [];
			allChars = (charsData as any).characters ?? [];
			if (plots.length > 0) {
				selectPlot(plots[0]);
			}
		} catch (e: any) {
			error = e.message;
		} finally {
			loading = false;
		}
	});
</script>

<AppShell title="Plots & Subplots">
	<div class="mx-auto flex max-w-5xl flex-col gap-4">
		<ProjectNav active="plots" />
		{#if !PROJECT}
			<NoProject />
		{:else if loading}
			<p style="color: var(--muted)">Loading plots...</p>
		{:else if error}
			<p role="alert" style="color: var(--danger)">{error}</p>
		{:else}
			<p class="text-xs" style="color: var(--muted)">
				Develop plots, link involved characters, and map resolution steps (<code>plots.xml</code>).
			</p>

			<div class="grid grid-cols-1 gap-4 md:grid-cols-12">
				<!-- Left Pane: Plot List + Filter -->
				<div
					class="flex flex-col gap-3 rounded-lg border p-3 md:col-span-4"
					style="border-color: var(--border); background: var(--surface)"
				>
					<div class="flex items-center gap-2">
						<div class="relative flex-1">
							<Search size={14} class="absolute left-2.5 top-2.5" style="color: var(--muted)" />
							<input
								class="w-full rounded-lg border py-1.5 pl-8 pr-2 text-xs"
								style="background: var(--bg); border-color: var(--border); color: var(--text)"
								placeholder="Filter plots..."
								bind:value={search}
							/>
						</div>
						<button
							type="button"
							class="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium"
							style="background: var(--accent); color: var(--accent-text)"
							onclick={createNewPlot}
						>
							<Plus size={14} /> Add
						</button>
					</div>

					{#if plots.length === 0}
						<EmptyState title="No plots yet">
							<button
								class="rounded-lg px-3 py-1.5 text-xs font-medium"
								style="background: var(--accent); color: var(--accent-text)"
								onclick={createNewPlot}
							>
								Add first plot
							</button>
						</EmptyState>
					{:else}
						<div class="flex max-h-[60vh] flex-col gap-1.5 overflow-y-auto pr-1">
							{#each filtered() as p (p.id)}
								<div
									class="flex cursor-pointer items-center gap-2.5 rounded-lg border p-2.5"
									style="border-color: {selectedId === p.id ? 'var(--accent)' : 'var(--border)'}; background: {selectedId === p.id ? 'color-mix(in srgb, var(--accent) 12%, var(--surface))' : 'var(--bg)'}"
									onclick={() => selectPlot(p)}
									role="button"
									tabindex="0"
									onkeydown={(e) => {
										if (e.key === 'Enter') selectPlot(p);
									}}
								>
									<span
										class="rounded px-1.5 py-0.5 text-[10px] font-bold text-white"
										style="background: {p.importance === '2' ? '#dc2626' : p.importance === '1' ? '#d97706' : '#6b7280'}"
									>
										{importanceBadge(p.importance)}
									</span>
									<div class="min-w-0 flex-1">
										<div class="truncate text-xs font-semibold">{p.name}</div>
										<div class="truncate text-[11px]" style="color: var(--muted)">
											{p.steps.length} step(s) · {p.characters.length} character(s)
										</div>
									</div>
									<button
										type="button"
										class="rounded p-1 opacity-70 hover:opacity-100"
										style="color: var(--danger)"
										title="Delete plot"
										onclick={(e) => {
											e.stopPropagation();
											void removePlot(p);
										}}
									>
										<Trash2 size={13} />
									</button>
								</div>
							{/each}
						</div>
					{/if}
				</div>

				<!-- Right Pane: Master-Detail Plot Editor (General Info & Resolution Steps tabs) -->
				<div
					class="flex flex-col gap-4 rounded-lg border p-4 md:col-span-8"
					style="border-color: var(--border); background: var(--surface)"
				>
					{#if !draft}
						<div class="flex min-h-[260px] flex-col items-center justify-center gap-2 text-center">
							<GitBranch size={28} style="color: var(--muted)" />
							<p class="text-sm" style="color: var(--muted)">
								Select a plot on the left or create a new one.
							</p>
						</div>
					{:else}
						<div class="flex items-center justify-between gap-2">
							<div class="flex gap-1 rounded-lg border p-1" style="border-color: var(--border)">
								<button
									type="button"
									class="rounded px-3 py-1 text-xs font-medium"
									style="background: {activePlotTab === 'infos' ? 'var(--accent)' : 'transparent'}; color: {activePlotTab === 'infos' ? 'var(--accent-text)' : 'var(--text)'}"
									onclick={() => (activePlotTab = 'infos')}
								>
									Plot Info & Characters
								</button>
								<button
									type="button"
									class="rounded px-3 py-1 text-xs font-medium"
									style="background: {activePlotTab === 'steps' ? 'var(--accent)' : 'transparent'}; color: {activePlotTab === 'steps' ? 'var(--accent-text)' : 'var(--text)'}"
									onclick={() => (activePlotTab = 'steps')}
								>
									Resolution Steps ({draft.steps.length})
								</button>
							</div>

							<button
								type="button"
								class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium"
								style="background: var(--accent); color: var(--accent-text); opacity: {saving ? 0.7 : 1}"
								onclick={saveDraft}
								disabled={saving || !draft.name.trim()}
							>
								{#if saved}<Check size={13} />{/if}
								{saving ? 'Saving...' : 'Save Plot'}
							</button>
						</div>

						{#if activePlotTab === 'infos'}
							<div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
								<div class="flex flex-col gap-1 sm:col-span-2">
									<label class="text-xs font-medium" style="color: var(--muted)" for="plot-name">Plot Name</label>
									<input
										id="plot-name"
										class="rounded-lg border px-3 py-2 text-sm"
										style="background: var(--bg); border-color: var(--border); color: var(--text)"
										bind:value={draft.name}
										oninput={() => (saved = false)}
										placeholder="Plot name"
									/>
								</div>
								<div class="flex flex-col gap-1">
									<label class="text-xs font-medium" style="color: var(--muted)" for="plot-imp">Importance</label>
									<select
										id="plot-imp"
										class="rounded-lg border px-2.5 py-2 text-sm"
										style="background: var(--bg); border-color: var(--border); color: var(--text)"
										bind:value={draft.importance}
										onchange={() => (saved = false)}
									>
										<option value="2">Main</option>
										<option value="1">Secondary</option>
										<option value="0">Minor</option>
									</select>
								</div>
							</div>

							<!-- Involved Characters (Desktop parity) -->
							<div class="flex flex-col gap-1.5">
								<span class="flex items-center gap-1 text-xs font-medium" style="color: var(--muted)">
									<Users size={13} /> Involved Characters
								</span>
								{#if allChars.length === 0}
									<p class="text-xs" style="color: var(--muted)">No characters in project yet.</p>
								{:else}
									<div class="flex flex-wrap gap-1.5">
										{#each allChars as c (c.id)}
											{@const linked = draft.characters.includes(c.id)}
											<button
												type="button"
												class="rounded-full border px-2.5 py-1 text-xs font-medium transition"
												style="border-color: {linked ? 'var(--accent)' : 'var(--border)'}; background: {linked ? 'var(--accent)' : 'var(--bg)'}; color: {linked ? 'var(--accent-text)' : 'var(--text)'}"
												onclick={() => toggleCharacterLink(c.id)}
											>
												{c.name}
											</button>
										{/each}
									</div>
								{/if}
							</div>

							<div class="flex flex-col gap-1">
								<label class="text-xs font-medium" style="color: var(--muted)" for="plot-summary">Summary</label>
								<input
									id="plot-summary"
									class="rounded-lg border px-3 py-2 text-sm"
									style="background: var(--bg); border-color: var(--border); color: var(--text)"
									bind:value={draft.summary}
									oninput={() => (saved = false)}
									placeholder="One-line plot summary"
								/>
							</div>

							<div class="flex flex-col gap-1">
								<label class="text-xs font-medium" style="color: var(--muted)" for="plot-desc">Description</label>
								<textarea
									id="plot-desc"
									class="w-full rounded-lg border px-3 py-2 text-sm"
									rows={4}
									style="background: var(--bg); border-color: var(--border); color: var(--text); resize: vertical"
									bind:value={draft.description}
									oninput={() => (saved = false)}
									placeholder="What is this plot or conflict about?"
								></textarea>
							</div>

							<div class="flex flex-col gap-1">
								<label class="text-xs font-medium" style="color: var(--muted)" for="plot-res">Resolution / Result</label>
								<textarea
									id="plot-res"
									class="w-full rounded-lg border px-3 py-2 text-sm"
									rows={3}
									style="background: var(--bg); border-color: var(--border); color: var(--text); resize: vertical"
									bind:value={draft.result}
									oninput={() => (saved = false)}
									placeholder="How is this plot resolved?"
								></textarea>
							</div>
						{:else}
							<!-- Resolution Steps Tab (Desktop Parity: Table + Stage Template Picker + Step Summary) -->
							<div class="flex flex-wrap items-center justify-between gap-2">
								<button
									type="button"
									class="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium"
									style="background: var(--accent); color: var(--accent-text)"
									onclick={() => addStep('New step', '')}
								>
									<Plus size={14} /> Add Step
								</button>

								<div class="flex items-center gap-1.5">
									<Sparkles size={14} style="color: var(--accent)" />
									<select
										class="rounded-lg border px-2.5 py-1.5 text-xs"
										style="background: var(--bg); border-color: var(--border); color: var(--text)"
										aria-label="Insert plot structure template"
										onchange={(e) => {
											const val = e.currentTarget.value;
											if (val) {
												insertStageTemplate(val);
												e.currentTarget.value = '';
											}
										}}
									>
										<option value="">+ Insert Structure Template...</option>
										{#each STEP_STAGE_GROUPS as g (g.group)}
											<option value={g.group}>{g.group} ({g.stages.length} steps)</option>
										{/each}
									</select>
								</div>
							</div>

							{#if draft.steps.length === 0}
								<p class="py-6 text-center text-xs" style="color: var(--muted)">
									No resolution steps yet. Add a step or pick a plot structure template above.
								</p>
							{:else}
								<div class="flex flex-col gap-1.5">
									{#each draft.steps as step, idx (step.id ?? idx)}
										<div
											class="flex items-center gap-2 rounded-lg border p-2"
											style="border-color: {selectedStepIdx === idx ? 'var(--accent)' : 'var(--border)'}; background: var(--bg)"
											onclick={() => (selectedStepIdx = idx)}
											role="button"
											tabindex="0"
											onkeydown={(e) => {
												if (e.key === 'Enter') selectedStepIdx = idx;
											}}
										>
											<span class="w-5 text-center text-xs font-semibold" style="color: var(--muted)">
												{idx + 1}
											</span>
											<input
												class="flex-1 rounded border px-2 py-1 text-xs font-medium"
												style="background: var(--surface); border-color: var(--border); color: var(--text)"
												bind:value={step.name}
												oninput={() => (saved = false)}
												placeholder="Step title"
											/>
											<input
												class="w-36 rounded border px-2 py-1 text-xs"
												style="background: var(--surface); border-color: var(--border); color: var(--muted)"
												bind:value={step.meta}
												oninput={() => (saved = false)}
												placeholder="Stage / Meta"
											/>
											<button
												type="button"
												class="rounded p-1"
												style="color: var(--muted)"
												title="Move step up"
												disabled={idx === 0}
												onclick={(e) => {
													e.stopPropagation();
													moveStep(idx, -1);
												}}
											>
												<ArrowUp size={13} />
											</button>
											<button
												type="button"
												class="rounded p-1"
												style="color: var(--muted)"
												title="Move step down"
												disabled={idx === draft.steps.length - 1}
												onclick={(e) => {
													e.stopPropagation();
													moveStep(idx, 1);
												}}
											>
												<ArrowDown size={13} />
											</button>
											<button
												type="button"
												class="rounded p-1"
												style="color: var(--danger)"
												title="Delete step"
												onclick={(e) => {
													e.stopPropagation();
													removeStep(idx);
												}}
											>
												<Trash2 size={13} />
											</button>
										</div>
									{/each}
								</div>

								{#if selectedStepIdx !== null && draft.steps[selectedStepIdx]}
									<div class="flex flex-col gap-1 rounded-lg border p-3" style="border-color: var(--border); background: var(--bg)">
										<label class="text-xs font-semibold" style="color: var(--muted)" for="step-detail-summary">
											Step {selectedStepIdx + 1} Summary ({draft.steps[selectedStepIdx].name || 'Untitled'})
										</label>
										<textarea
											id="step-detail-summary"
											class="w-full rounded-lg border px-3 py-2 text-sm"
											rows={4}
											style="background: var(--surface); border-color: var(--border); color: var(--text); resize: vertical"
											bind:value={draft.steps[selectedStepIdx].summary}
											oninput={() => (saved = false)}
											placeholder="Describe what happens in this plot step..."
										></textarea>
									</div>
								{/if}
							{/if}
						{/if}
					{/if}
				</div>
			</div>
		{/if}
	</div>
</AppShell>
