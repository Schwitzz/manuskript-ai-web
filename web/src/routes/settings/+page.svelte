<script lang="ts">
	import AppShell from '#lib/components/AppShell.svelte';
	import NoProject from '#lib/components/NoProject.svelte';
	import { project } from '#lib/stores/project.svelte.ts';
	import AppearanceSettings from '#lib/components/AppearanceSettings.svelte';
	import { Palette, BookOpen, FileText, Check } from '@lucide/svelte';
	import { call } from '#lib/api';
	import { page } from '$app/state';

	const PROJECT_NAME = $derived(project.name ?? '');

	let activeTab = $state<'general' | 'summary' | 'appearance'>(
		page.url.searchParams.get('tab') === 'summary'
			? 'summary'
			: page.url.searchParams.get('tab') === 'appearance'
				? 'appearance'
				: 'general'
	);
	let saving = $state(false);
	let saved = $state(true);
	let error = $state('');

	let bookInfo = $state<Record<string, string>>({});
	let snowflakeSummary = $state<Record<string, string>>({});

	let loading = $state(true);

	// Exact parity with Desktop Manuskript's General Info (`infos.txt`) fields
	const generalFields = [
		{ key: 'Title', label: 'Title', placeholder: 'Book title' },
		{ key: 'Subtitle', label: 'Subtitle', placeholder: 'Book subtitle' },
		{ key: 'Serie', label: 'Series', placeholder: 'Series name' },
		{ key: 'Volume', label: 'Volume', placeholder: 'e.g., 1' },
		{ key: 'Genre', label: 'Genre', placeholder: 'e.g., Science Fiction, Fantasy' },
		{ key: 'License', label: 'License', placeholder: 'e.g., All rights reserved, CC BY-SA' },
		{ key: 'Author', label: 'Author', placeholder: 'Your name' },
		{ key: 'Email', label: 'Email', placeholder: 'author@example.com' }
	];

	// Exact parity with Desktop Manuskript's Snowflake Summary (`summary.txt`) fields
	const summaryFields = [
		{
			key: 'Situation',
			label: 'Situation ("What if...?")',
			hint: "The basic situation, in the form of a 'What if...?' question (e.g. 'What if the most dangerous wizard couldn't kill a baby?').",
			placeholder: 'What if...',
			rows: 2,
			showPages: false
		},
		{
			key: 'Sentence',
			label: 'One-Sentence Summary',
			hint: 'Take time to craft a ~50-word one-sentence summary of your book.',
			placeholder: 'One sentence summarizing the core story arc...',
			rows: 2,
			showPages: false
		},
		{
			key: 'Paragraph',
			label: 'One-Paragraph Summary',
			hint: 'Expand your sentence into a full paragraph (setup, major disasters, and ending).',
			placeholder: 'One-paragraph summary...',
			rows: 4,
			showPages: false
		},
		{
			key: 'Page',
			label: 'One-Page Synopsis',
			hint: 'Expand each sentence of your paragraph into a full paragraph (~1 page).',
			placeholder: 'One-page synopsis...',
			rows: 6,
			showPages: true
		},
		{
			key: 'Full',
			label: 'Full Summary',
			hint: 'Expand into a complete multi-page synopsis covering every major character and plot turn.',
			placeholder: 'Full story summary...',
			rows: 10,
			showPages: true
		}
	];

	function countWords(text: string | undefined): number {
		if (!text || !text.trim()) return 0;
		return text.trim().split(/\s+/).filter(Boolean).length;
	}

	function wordCountLabel(text: string | undefined, showPages: boolean): string {
		const wc = countWords(text);
		if (showPages) {
			const pages = Math.floor(wc / 25) / 10;
			return `Words: ${wc.toLocaleString()} (~${pages} pages)`;
		}
		return `Words: ${wc.toLocaleString()}`;
	}

	function readKey(record: Record<string, string>, key: string): string {
		return record[key] ?? record[key.toLowerCase()] ?? (key === 'Serie' ? (record['series'] ?? '') : '');
	}

	async function loadData() {
		if (!PROJECT_NAME) {
			loading = false;
			return;
		}
		try {
			loading = true;
			error = '';
			const data = await call('GET /api/projects/{name}/info', {
				params: { name: PROJECT_NAME }
			});
			const rawInfo = (data as any).info || {};
			const rawSummary = (data as any).summary || {};
			const normalizedInfo: Record<string, string> = {};
			for (const f of generalFields) {
				normalizedInfo[f.key] = readKey(rawInfo, f.key);
			}
			const normalizedSummary: Record<string, string> = {};
			for (const f of summaryFields) {
				normalizedSummary[f.key] = readKey(rawSummary, f.key);
			}
			bookInfo = normalizedInfo;
			snowflakeSummary = normalizedSummary;
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
		} catch (e: any) {
			error = e.message;
		} finally {
			saving = false;
		}
	}

	function updateField(key: string, value: string) {
		bookInfo = { ...bookInfo, [key]: value };
		saved = false;
	}

	function updateSummaryField(key: string, value: string) {
		snowflakeSummary = { ...snowflakeSummary, [key]: value };
		saved = false;
	}

	$effect(() => {
		const urlTab = page.url.searchParams.get('tab');
		if (urlTab === 'summary' || urlTab === 'general' || urlTab === 'appearance') {
			activeTab = urlTab;
		}
	});

	$effect(() => {
		if (PROJECT_NAME) {
			void loadData();
		} else {
			loading = false;
		}
	});
</script>

<AppShell title="Title Properties & Summary">
	<div class="mx-auto flex max-w-2xl flex-col gap-6">
		<!-- Tabs matching Desktop Manuskript: General (Title Properties), Summary (Snowflake), Appearance -->
		<div class="flex gap-1 rounded-lg border p-1" style="border-color: var(--border); background: var(--surface)" role="tablist">
			<button
				class="flex-1 rounded-md px-3 py-1.5 text-sm font-medium"
				style="background: {activeTab === 'general' ? 'var(--accent)' : 'transparent'}; color: {activeTab === 'general' ? 'var(--accent-text)' : 'var(--text)'}"
				onclick={() => (activeTab = 'general')}
				role="tab"
				aria-selected={activeTab === 'general'}
			>
				<BookOpen size={15} class="mr-1 inline" />
				Title Properties
			</button>
			<button
				class="flex-1 rounded-md px-3 py-1.5 text-sm font-medium"
				style="background: {activeTab === 'summary' ? 'var(--accent)' : 'transparent'}; color: {activeTab === 'summary' ? 'var(--accent-text)' : 'var(--text)'}"
				onclick={() => (activeTab = 'summary')}
				role="tab"
				aria-selected={activeTab === 'summary'}
			>
				<FileText size={15} class="mr-1 inline" />
				Summary
			</button>
			<button
				class="flex-1 rounded-md px-3 py-1.5 text-sm font-medium"
				style="background: {activeTab === 'appearance' ? 'var(--accent)' : 'transparent'}; color: {activeTab === 'appearance' ? 'var(--accent-text)' : 'var(--text)'}"
				onclick={() => (activeTab = 'appearance')}
				role="tab"
				aria-selected={activeTab === 'appearance'}
			>
				<Palette size={15} class="mr-1 inline" />
				Appearance
			</button>
		</div>

		{#if activeTab === 'appearance'}
			<section class="flex flex-col gap-4 rounded-lg border p-4" style="border-color: var(--border); background: var(--surface)">
				<div class="flex items-center gap-2">
					<Palette size={20} style="color: var(--accent)" />
					<h2 class="text-lg font-semibold">Appearance & 32 Colour Schemes</h2>
				</div>
				<AppearanceSettings />
			</section>
		{:else if !PROJECT_NAME}
			<NoProject />
		{:else if loading}
			<p class="py-8 text-center" style="color: var(--muted)">Loading project properties...</p>
		{:else if error}
			<p class="rounded-lg border p-4 text-sm" style="border-color: var(--danger); color: var(--danger)">{error}</p>
		{:else if activeTab === 'general'}
			<!-- Title & Book Properties (General Tab) -->
			<section class="flex flex-col gap-4 rounded-lg border p-4" style="border-color: var(--border); background: var(--surface)">
				<div class="flex items-center justify-between">
					<div>
						<div class="flex items-center gap-2">
							<BookOpen size={20} style="color: var(--accent)" />
							<h2 class="text-lg font-semibold">Book & Title Properties</h2>
						</div>
						<p class="text-xs" style="color: var(--muted)">
							Enter information about your book and yourself (saved in <code>infos.txt</code>).
						</p>
					</div>
					<button
						class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium"
						style="background: var(--accent); color: var(--accent-text); opacity: {saving ? 0.7 : 1}"
						onclick={saveInfo}
						disabled={saving}
					>
						{#if saving}
							<span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"></span>
						{:else if saved}
							<Check size={14} />
						{/if}
						{saving ? 'Saving...' : 'Save'}
					</button>
				</div>

				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					{#each generalFields as field (field.key)}
						<div class="flex flex-col gap-1">
							<label class="text-xs font-medium" style="color: var(--muted)" for={`info-${field.key}`}>{field.label}</label>
							<input
								id={`info-${field.key}`}
								class="rounded-lg border px-3 py-2 text-sm"
								style="background: var(--bg); border-color: var(--border); color: var(--text)"
								value={bookInfo[field.key] || ''}
								oninput={(e) => updateField(field.key, (e.target as HTMLInputElement).value)}
								placeholder={field.placeholder}
							/>
						</div>
					{/each}
				</div>
			</section>
		{:else}
			<!-- Snowflake Summary Tab -->
			<section class="flex flex-col gap-4 rounded-lg border p-4" style="border-color: var(--border); background: var(--surface)">
				<div class="flex items-center justify-between">
					<div>
						<div class="flex items-center gap-2">
							<FileText size={20} style="color: var(--accent)" />
							<h2 class="text-lg font-semibold">Snowflake Summary</h2>
						</div>
						<p class="text-xs" style="color: var(--muted)">
							Develop your story from a 'What if...?' situation to a full synopsis (saved in <code>summary.txt</code>).
						</p>
					</div>
					<button
						class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium"
						style="background: var(--accent); color: var(--accent-text); opacity: {saving ? 0.7 : 1}"
						onclick={saveSummary}
						disabled={saving}
					>
						{#if saving}
							<span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"></span>
						{:else if saved}
							<Check size={14} />
						{/if}
						{saving ? 'Saving...' : 'Save'}
					</button>
				</div>

				<div class="flex flex-col gap-4">
					{#each summaryFields as field (field.key)}
						<div class="flex flex-col gap-1">
							<div class="flex items-center justify-between">
								<label class="text-xs font-semibold" style="color: var(--text)" for={`snowflake-${field.key}`}>
									{field.label}
								</label>
								<span class="text-xs" style="color: var(--muted)">
									{wordCountLabel(snowflakeSummary[field.key], field.showPages)}
								</span>
							</div>
							<p class="text-xs" style="color: var(--muted)">{field.hint}</p>
							<textarea
								id={`snowflake-${field.key}`}
								class="w-full rounded-lg border px-3 py-2 text-sm"
								rows={field.rows}
								style="background: var(--bg); border-color: var(--border); color: var(--text); resize: vertical"
								value={snowflakeSummary[field.key] || ''}
								oninput={(e) => updateSummaryField(field.key, (e.target as HTMLTextAreaElement).value)}
								placeholder={field.placeholder}
							></textarea>
						</div>
					{/each}
				</div>
			</section>
		{/if}
	</div>
</AppShell>
