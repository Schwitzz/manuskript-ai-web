<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { call, csrfToken, ApiError } from '#lib/api.ts';
	import { project, type ProjectItem } from '#lib/stores/project.svelte.ts';
	import { FolderOpen, FolderPlus, Upload, RefreshCw } from '@lucide/svelte';
	import { onMount } from 'svelte';

	let {
		notice = '',
		onProjectReady
	}: {
		notice?: string;
		onProjectReady?: (name: string) => void;
	} = $props();

	let projects = $state<ProjectItem[]>([]);
	let samples = $state<string[]>([]);
	let loadingList = $state(true);

	// Create form state
	let newName = $state('');
	let newTitle = $state('');
	let newSample = $state('');
	let creating = $state(false);
	let createError = $state('');

	// Import form state
	let importFile = $state<File | null>(null);
	let importName = $state('');
	let importing = $state(false);
	let importError = $state('');

	onMount(async () => {
		await refreshProjects();
		try {
			const s = await call('GET /api/projects/samples');
			samples = s.samples ?? [];
		} catch {}
	});

	async function refreshProjects() {
		loadingList = true;
		try {
			const data = await call('GET /api/projects');
			projects = ((data as any).projects ?? []) as ProjectItem[];
		} catch {
			projects = [];
		} finally {
			loadingList = false;
		}
	}

	function activateProject(name: string) {
		project.select(name);
		if (onProjectReady) {
			onProjectReady(name);
		} else if (!page.url.pathname.startsWith('/write')) {
			goto('/write');
		}
	}

	async function handleCreate(e: SubmitEvent) {
		e.preventDefault();
		createError = '';
		const clean = newName.trim();
		if (!clean) {
			createError = 'Project name is required';
			return;
		}
		creating = true;
		try {
			await call('POST /api/projects', {
				body: {
					name: clean,
					title: newTitle.trim() || clean,
					sample: newSample || undefined
				}
			});
			newName = '';
			newTitle = '';
			newSample = '';
			activateProject(clean);
		} catch (err: unknown) {
			createError = err instanceof ApiError ? err.message : 'Failed to create project';
		} finally {
			creating = false;
		}
	}

	function onFilePicked(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const f = input.files?.[0] ?? null;
		importFile = f;
		if (f && !importName.trim()) {
			importName = f.name.replace(/\.(msk|zip)$/i, '');
		}
	}

	async function handleImport(e: SubmitEvent) {
		e.preventDefault();
		importError = '';
		if (!importFile) {
			importError = 'Choose a .msk or .zip project file first';
			return;
		}
		importing = true;
		try {
			const fd = new FormData();
			fd.append('file', importFile);
			const isMsk = importFile.name.toLowerCase().endsWith('.msk');
			const cleanName = importName.trim() || importFile.name.replace(/\.(msk|zip)$/i, '');
			const url = isMsk
				? `/api/projects/import-msk?name=${encodeURIComponent(cleanName)}`
				: '/api/projects/upload';
			const res = await fetch(url, {
				method: 'POST',
				headers: { 'x-csrf-token': csrfToken() },
				credentials: 'same-origin',
				body: fd
			});
			if (!res.ok) {
				let msg = `Import failed (${res.status})`;
				try {
					const j = await res.json();
					if (typeof j.detail === 'string') msg = j.detail;
				} catch {}
				throw new Error(msg);
			}
			const data = await res.json();
			const openedName = data.name || cleanName;
			activateProject(openedName);
		} catch (err: any) {
			importError = err.message || 'Could not import project';
		} finally {
			importing = false;
		}
	}
</script>

<div class="mx-auto flex w-full max-w-3xl flex-col gap-5 py-6">
	<div class="flex flex-col items-center gap-2 text-center">
		<p class="text-base font-semibold" style="color: var(--text)">No project selected</p>
		{#if notice}
			<p class="text-xs" style="color: var(--muted)">{notice}</p>
		{:else}
			<p class="text-xs" style="color: var(--muted)">
				Load an existing project, import a project archive, or create a new project below.
			</p>
		{/if}
		<button
			type="button"
			class="mt-1 rounded-lg border px-4 py-1.5 text-xs font-medium"
			style="border-color: var(--border); background: var(--surface); color: var(--text)"
			onclick={() => goto('/more')}
		>
			Choose or create a project
		</button>
	</div>

	<div class="grid grid-cols-1 gap-4 md:grid-cols-3">
		<!-- 1. Load Existing Project -->
		<section
			class="flex flex-col gap-3 rounded-xl border p-4"
			style="border-color: var(--border); background: var(--surface)"
			aria-label="Load Project"
		>
			<div class="flex items-center justify-between">
				<h2 class="flex items-center gap-2 text-sm font-semibold">
					<FolderOpen size={17} style="color: var(--accent)" /> Load Project
				</h2>
				<button
					type="button"
					class="tap rounded p-1"
					title="Refresh projects"
					onclick={refreshProjects}
					style="color: var(--muted)"
				>
					<RefreshCw size={14} />
				</button>
			</div>
			{#if loadingList}
				<p class="text-xs" style="color: var(--muted)">Checking server projects...</p>
			{:else if projects.length === 0}
				<p class="text-xs" style="color: var(--muted)">
					No projects found on the server yet. Create or import one to begin.
				</p>
			{:else}
				<ul class="flex flex-col gap-1.5">
					{#each projects as p (p.name)}
						<li>
							<button
								type="button"
								onclick={() => activateProject(p.name)}
								class="flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-xs font-medium transition hover:opacity-90"
								style="background: var(--bg); border-color: var(--border); color: var(--text)"
							>
								<FolderOpen size={14} style="color: var(--accent)" class="shrink-0" />
								<span class="flex-1 truncate">{p.title || p.name}</span>
							</button>
						</li>
					{/each}
				</ul>
			{/if}
		</section>

		<!-- 2. Import Project (.msk / .zip) -->
		<section
			class="flex flex-col gap-3 rounded-xl border p-4"
			style="border-color: var(--border); background: var(--surface)"
			aria-label="Import Project"
		>
			<h2 class="flex items-center gap-2 text-sm font-semibold">
				<Upload size={17} style="color: var(--accent)" /> Import Project
			</h2>
			<form onsubmit={handleImport} class="flex flex-col gap-2.5" novalidate>
				<label class="flex flex-col gap-1">
					<span class="text-xs" style="color: var(--muted)">Archive (.msk or .zip)</span>
					<input
						type="file"
						accept=".msk,.zip"
						onchange={onFilePicked}
						class="rounded border px-2 py-1.5 text-xs"
						style="background: var(--bg); border-color: var(--border); color: var(--text)"
					/>
				</label>
				<label class="flex flex-col gap-1">
					<span class="text-xs" style="color: var(--muted)">Project Name</span>
					<input
						type="text"
						bind:value={importName}
						placeholder="my-imported-novel"
						autocomplete="off"
						class="rounded border px-2.5 py-1.5 text-xs"
						style="background: var(--bg); border-color: var(--border); color: var(--text)"
					/>
				</label>
				{#if importError}
					<p role="alert" class="text-xs" style="color: var(--danger)">{importError}</p>
				{/if}
				<button
					type="submit"
					disabled={importing}
					class="mt-auto rounded-lg px-3 py-2 text-xs font-medium disabled:opacity-60"
					style="background: var(--accent); color: var(--accent-text)"
				>
					{importing ? 'Importing...' : 'Import & Open'}
				</button>
			</form>
		</section>

		<!-- 3. Create New Project -->
		<section
			class="flex flex-col gap-3 rounded-xl border p-4"
			style="border-color: var(--border); background: var(--surface)"
			aria-label="Create New Project"
		>
			<h2 class="flex items-center gap-2 text-sm font-semibold">
				<FolderPlus size={17} style="color: var(--accent)" /> Create Project
			</h2>
			<form onsubmit={handleCreate} class="flex flex-col gap-2.5" novalidate>
				<label class="flex flex-col gap-1">
					<span class="text-xs" style="color: var(--muted)">Project Name</span>
					<input
						type="text"
						bind:value={newName}
						placeholder="my-novel"
						autocomplete="off"
						class="rounded border px-2.5 py-1.5 text-xs"
						style="background: var(--bg); border-color: var(--border); color: var(--text)"
					/>
				</label>
				<label class="flex flex-col gap-1">
					<span class="text-xs" style="color: var(--muted)">Title (optional)</span>
					<input
						type="text"
						bind:value={newTitle}
						placeholder="My Novel"
						autocomplete="off"
						class="rounded border px-2.5 py-1.5 text-xs"
						style="background: var(--bg); border-color: var(--border); color: var(--text)"
					/>
				</label>
				{#if samples.length > 0}
					<label class="flex flex-col gap-1">
						<span class="text-xs" style="color: var(--muted)">Sample (optional)</span>
						<select
							bind:value={newSample}
							class="rounded border px-2 py-1.5 text-xs"
							style="background: var(--bg); border-color: var(--border); color: var(--text)"
						>
							<option value="">Blank project</option>
							{#each samples as s}<option value={s}>{s}</option>{/each}
						</select>
					</label>
				{/if}
				{#if createError}
					<p role="alert" class="text-xs" style="color: var(--danger)">{createError}</p>
				{/if}
				<button
					type="submit"
					disabled={creating}
					class="mt-auto rounded-lg px-3 py-2 text-xs font-medium disabled:opacity-60"
					style="background: var(--accent); color: var(--accent-text)"
				>
					{creating ? 'Creating...' : 'Create & Open'}
				</button>
			</form>
		</section>
	</div>
</div>
