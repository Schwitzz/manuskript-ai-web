<script lang="ts">
	import AppShell from '#lib/components/AppShell.svelte';
	import AppearanceSettings from '#lib/components/AppearanceSettings.svelte';
	import InstallPrompt from '#lib/components/InstallPrompt.svelte';
	import TwoFactor from '#lib/components/TwoFactor.svelte';
	import { auth } from '#lib/stores/auth.svelte.ts';
	import { project, type ProjectItem } from '#lib/stores/project.svelte.ts';
	import {
		LogOut, Brain, Settings2, Tag, UserPlus, FolderPlus, FolderOpen,
		Trash2, BookmarkPlus, LayoutTemplate, BookOpen, FileText, Users,
		GitBranch, Globe, ListTree, Layers, PenLine, Palette
	} from '@lucide/svelte';
	import { goto } from '$app/navigation';
	import { call, ApiError } from '#lib/api.ts';
	import { onMount } from 'svelte';

	let projects = $state<ProjectItem[]>([]);
	let creating = $state(false);
	let showCreateForm = $state(false);
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

	// Desktop Moduskript Workspace Navigation Grid
	const workspaceItems = [
		{ href: '/settings?tab=general', label: 'Title Properties', desc: 'Book title, author, series & genre', icon: BookOpen },
		{ href: '/settings?tab=summary', label: 'Snowflake Summary', desc: 'Situation, sentence, paragraph & full synopsis', icon: FileText },
		{ href: '/characters', label: 'Characters', desc: 'POV, motivation, goals, conflicts & traits', icon: Users },
		{ href: '/plots', label: 'Plots & Subplots', desc: 'Story arcs, characters & resolution steps', icon: GitBranch },
		{ href: '/world', label: 'World Builder', desc: 'Places, cultures, rules & world hierarchy', icon: Globe },
		{ href: '/outline', label: 'Outline', desc: 'Chapters, scenes, notes & tree/table views', icon: ListTree },
		{ href: '/whiteboard', label: 'Board (Whiteboard)', desc: 'Visual canvas, shapes, notes & connections', icon: Layers },
		{ href: '/write', label: 'Writing Space', desc: 'Markdown editor with Readable / MD Code mode', icon: PenLine },
		{ href: '/labels', label: 'Labels & Statuses', desc: 'Scene labels, colors & draft statuses', icon: Tag }
	];

	onMount(async () => {
		await Promise.all([loadProjects(), loadTemplates()]);
		try {
			const data = await call('GET /api/projects/samples');
			samples = data.samples;
		} catch {
			/* no samples */
		}
	});

	async function loadProjects() {
		projects = await project.fetchProjects();
	}

	async function loadTemplates() {
		try {
			templates = (await call('GET /api/templates')).templates;
		} catch {
			/* no templates */
		}
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
			showCreateForm = false;
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
		if (!confirm(`Delete project "${name}"? This moves it to the trash.`)) return;
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

<AppShell title="Workspace & Settings">
	<div class="mx-auto flex max-w-3xl flex-col gap-6">
		<!-- 1. Projects & Templates Card -->
		<section class="flex flex-col gap-4 rounded-xl border p-4" style="border-color: var(--border); background: var(--surface)">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2">
					<FolderOpen size={18} style="color: var(--accent)" />
					<h2 class="text-sm font-semibold">Projects</h2>
				</div>
				<button
					type="button"
					class="flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium"
					style="background: var(--accent); color: var(--accent-text)"
					onclick={() => (showCreateForm = !showCreateForm)}
				>
					<FolderPlus size={14} /> New Project
				</button>
			</div>

			{#if projects.length === 0}
				<p style="color: var(--muted); font-size: 0.875rem;">No projects yet. Create one below.</p>
			{:else}
				<ul class="grid grid-cols-1 gap-2 sm:grid-cols-2">
					{#each projects as p (p.name)}
						<li class="flex items-center gap-1.5 rounded-lg border p-1.5" style="border-color: {project.name === p.name ? 'var(--accent)' : 'var(--border)'}; background: var(--bg)">
							<button
								class="flex flex-1 items-center gap-2.5 rounded-md px-3 py-1.5 text-left"
								style="background: {project.name === p.name ? 'var(--accent)' : 'transparent'}; color: {project.name === p.name ? 'var(--accent-text)' : 'var(--text)'}"
								onclick={() => handleSelect(p)}
							>
								<FolderOpen size={16} />
								<span class="flex-1 truncate text-sm font-medium">{p.title || p.name}</span>
							</button>
							<button
								class="tap rounded p-1.5"
								style="color: var(--muted)"
								onclick={() => startSaveTemplate(p)}
								title="Save as template"
							>
								<BookmarkPlus size={15} />
							</button>
							<button
								class="tap rounded p-1.5"
								style="color: var(--danger)"
								onclick={() => handleDelete(p.name)}
								title="Delete project"
							>
								<Trash2 size={15} />
							</button>
						</li>
					{/each}
				</ul>
			{/if}

			{#if savingFrom}
				<form onsubmit={handleSaveTemplate} class="flex flex-col gap-3 rounded-lg border p-3" style="border-color: var(--accent); background: var(--bg)">
					<h3 class="text-sm font-medium">Save "{savingFrom}" as a template</h3>
					<label class="flex flex-col gap-1">
						<span class="text-xs">Template name</span>
						<input
							class="rounded-lg border px-3 py-2 text-sm"
							style="background: var(--surface); border-color: var(--border)"
							bind:value={templateName}
							autocomplete="off"
							maxlength="100"
							required
						/>
					</label>
					<label class="flex items-center gap-2 text-sm">
						<input type="checkbox" bind:checked={templateKeepText} />
						Keep the written text (otherwise only the structure is saved)
					</label>
					{#if error}<p role="alert" style="color: var(--danger); font-size: 0.875rem;">{error}</p>{/if}
					<div class="flex gap-2">
						<button
							class="flex-1 rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-60"
							style="background: var(--accent); color: var(--accent-text)"
							disabled={savingTemplate}
						>
							{savingTemplate ? 'Saving...' : 'Save template'}
						</button>
						<button
							type="button"
							class="rounded-lg border px-4 py-2 text-sm"
							style="border-color: var(--border)"
							onclick={() => (savingFrom = null)}
						>
							Cancel
						</button>
					</div>
				</form>
			{/if}

			{#if templates.length > 0}
				<div class="border-t pt-3" style="border-color: var(--border)">
					<h3 class="mb-2 flex items-center gap-2 text-xs font-semibold uppercase" style="color: var(--muted)">
						<LayoutTemplate size={14} /> Saved Templates
					</h3>
					<ul class="flex flex-wrap gap-2">
						{#each templates as t (t)}
							<li class="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs" style="background: var(--bg); border-color: var(--border)">
								<span class="truncate font-medium">{t}</span>
								<button
									class="tap rounded p-0.5"
									style="color: var(--danger)"
									onclick={() => handleDeleteTemplate(t)}
									title="Delete template"
								>
									<Trash2 size={14} />
								</button>
							</li>
						{/each}
					</ul>
				</div>
			{/if}

			<!-- Create Project Form (always rendered for quick access & tests) -->
			<div class="border-t pt-3" style="border-color: var(--border)">
				<h3 class="mb-2 flex items-center gap-2 text-xs font-semibold uppercase" style="color: var(--muted)">
					<FolderPlus size={14} /> Create Project
				</h3>
				<form onsubmit={handleCreate} class="grid grid-cols-1 gap-3 sm:grid-cols-2">
					<label class="flex flex-col gap-1">
						<span class="text-xs">Name</span>
						<input
							class="rounded-lg border px-3 py-2 text-sm"
							style="background: var(--bg); border-color: var(--border)"
							bind:value={newProjectName}
							autocomplete="off"
							placeholder="my-novel"
							required
						/>
					</label>
					<label class="flex flex-col gap-1">
						<span class="text-xs">Title (optional)</span>
						<input
							class="rounded-lg border px-3 py-2 text-sm"
							style="background: var(--bg); border-color: var(--border)"
							bind:value={newProjectTitle}
							placeholder="My Novel"
						/>
					</label>
					{#if templates.length > 0}
						<label class="flex flex-col gap-1">
							<span class="text-xs">Start from a template</span>
							<select
								class="rounded-lg border px-3 py-2 text-sm"
								style="background: var(--bg); border-color: var(--border)"
								bind:value={newTemplate}
								onchange={() => {
									if (newTemplate) newSample = '';
								}}
							>
								<option value="">None (blank project)</option>
								{#each templates as t}<option value={t}>{t}</option>{/each}
							</select>
						</label>
					{/if}
					{#if samples.length > 0}
						<label class="flex flex-col gap-1">
							<span class="text-xs">Or start from a sample</span>
							<select
								class="rounded-lg border px-3 py-2 text-sm"
								style="background: var(--bg); border-color: var(--border)"
								bind:value={newSample}
								onchange={() => {
									if (newSample) newTemplate = '';
								}}
							>
								<option value="">None (blank project)</option>
								{#each samples as s}<option value={s}>{s}</option>{/each}
							</select>
						</label>
					{/if}
					{#if error}
						<p role="alert" class="sm:col-span-2" style="color: var(--danger); font-size: 0.875rem;">{error}</p>
					{/if}
					<div class="sm:col-span-2">
						<button
							class="w-full rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-60"
							style="background: var(--accent); color: var(--accent-text)"
							disabled={creating}
						>
							{creating ? 'Creating...' : 'Create Project'}
						</button>
					</div>
				</form>
			</div>
		</section>

		<!-- 2. Story & Book Workspace Navigation (Desktop Parity Grid) -->
		<section class="flex flex-col gap-3 rounded-xl border p-4" style="border-color: var(--border); background: var(--surface)">
			<div class="flex items-center justify-between">
				<h2 class="text-sm font-semibold">Story & Manuscript Workspace</h2>
				{#if project.name}
					<span class="rounded-full px-2.5 py-0.5 text-xs font-medium" style="background: var(--bg); color: var(--accent)">
						Active: {project.name}
					</span>
				{/if}
			</div>
			<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
				{#each workspaceItems as item (item.href)}
					<button
						type="button"
						class="flex items-start gap-3 rounded-lg border p-3 text-left transition hover:opacity-90"
						style="background: var(--bg); border-color: var(--border)"
						onclick={() => goto(item.href)}
					>
						<div class="mt-0.5 rounded-md p-1.5" style="background: var(--surface); color: var(--accent)">
							<item.icon size={18} />
						</div>
						<div class="min-w-0 flex-1">
							<div class="text-sm font-semibold">{item.label}</div>
							<div class="text-xs leading-snug" style="color: var(--muted)">{item.desc}</div>
						</div>
					</button>
				{/each}
			</div>
		</section>

		<!-- 3. AI Assistant, Users & App Configuration -->
		<section class="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
			<button
				class="flex items-center gap-3 rounded-xl border px-4 py-3 text-left font-medium"
				style="background: var(--surface); border-color: var(--border)"
				onclick={() => goto('/more/ai')}
			>
				<Brain size={20} style="color: var(--accent)" />
				<div>
					<div class="text-sm font-semibold">AI Settings</div>
					<div class="text-xs" style="color: var(--muted)">Providers, models & prompts</div>
				</div>
			</button>
			<button
				class="flex items-center gap-3 rounded-xl border px-4 py-3 text-left font-medium"
				style="background: var(--surface); border-color: var(--border)"
				onclick={() => goto('/settings')}
			>
				<Settings2 size={20} style="color: var(--accent)" />
				<div>
					<div class="text-sm font-semibold">App Settings</div>
					<div class="text-xs" style="color: var(--muted)">Title info, summary & themes</div>
				</div>
			</button>
			<button
				class="flex items-center gap-3 rounded-xl border px-4 py-3 text-left font-medium"
				style="background: var(--surface); border-color: var(--border)"
				onclick={() => goto('/register')}
			>
				<UserPlus size={20} style="color: var(--accent)" />
				<div>
					<div class="text-sm font-semibold">Create user</div>
					<div class="text-xs" style="color: var(--muted)">Manage accounts</div>
				</div>
			</button>
		</section>

		<!-- 4. Appearance & Theme Switcher -->
		<section class="flex flex-col gap-3 rounded-xl border p-4" style="border-color: var(--border); background: var(--surface)">
			<div class="flex items-center gap-2">
				<Palette size={18} style="color: var(--accent)" />
				<h2 class="text-sm font-semibold">Appearance & 32 Colour Schemes</h2>
			</div>
			<AppearanceSettings />
		</section>

		<!-- 5. Two-Factor Auth & Session -->
		<TwoFactor />
		<InstallPrompt />
		<button
			class="flex w-full items-center justify-center gap-2 rounded-xl border px-4 py-3 font-medium"
			style="background: var(--surface); border-color: var(--border); color: var(--danger)"
			onclick={() => auth.logout()}
		>
			<LogOut size={18} /> Log out
		</button>
	</div>
</AppShell>
