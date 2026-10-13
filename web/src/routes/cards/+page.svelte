<script lang="ts">
	import AppShell from '#lib/components/AppShell.svelte';
	import NoProject from '#lib/components/NoProject.svelte';
	import { project } from '#lib/stores/project.svelte.ts';
	import { call, ApiError } from '#lib/api';
	import { toItems, type LabelDef, type OutlineItem } from '#lib/outline.ts';
	import { onMount } from 'svelte';
	import Whiteboard from '#lib/components/Whiteboard.svelte';

	const PROJECT = project.name ?? '';

	let outline = $state<OutlineItem[]>([]);
	let labels = $state<LabelDef[]>([]);
	let statusList = $state<string[]>([]);
	let loading = $state(true);
	let error = $state('');

	function msg(e: unknown, fallback: string): string {
		return e instanceof ApiError || e instanceof Error ? e.message : fallback;
	}

	async function load() {
		const [o, l] = await Promise.all([
			call('GET /api/projects/{name}/outline', { params: { name: PROJECT } }),
			call('GET /api/projects/{name}/labels', { params: { name: PROJECT } })
		]);
		outline = toItems(o.items);
		labels = l.labels;
		statusList = l.status;
	}

	onMount(async () => {
		if (!PROJECT) {
			loading = false;
			return;
		}
		try {
			await load();
		} catch (e) {
			error = msg(e, 'Failed to load cards');
		} finally {
			loading = false;
		}
	});
</script>

<AppShell title="Cards">
<Whiteboard project={PROJECT} items={outline} {labels} {statusList} />
</AppShell>
