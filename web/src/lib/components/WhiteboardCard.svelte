<script lang="ts" generics="T">
	import { Handle, Position } from '@xyflow/svelte';
	import { FileText, Folder } from '@lucide/svelte';

	let { data }: { data: T } = $props();

	const d = $derived(data as {
		id: number;
		title: string;
		type: string;
		summary: string;
		words: number;
		label: string;
		color: string;
		status: string;
	});
</script>

<div
	class="w-64 rounded-lg border shadow-sm transition-shadow hover:shadow-md"
	style="background: var(--surface); border-color: {d.color || 'var(--border)'}"
>
	<!-- Label color bar -->
	{#if d.color}
	<div class="h-1.5 rounded-t-lg" style="background: {d.color}"></div>
	{/if}

	<div class="p-3">
		<!-- Title row -->
		<div class="flex items-center gap-2">
			{#if d.type === 'folder'}
				<Folder size={15} style="color: var(--muted)" />
			{:else}
				<FileText size={15} style="color: var(--muted)" />
			{/if}
			<span class="min-w-0 flex-1 truncate text-sm font-medium">{d.title}</span>
		</div>

		<!-- Summary -->
		{#if d.summary}
			<p class="mt-1.5 line-clamp-2 text-xs leading-relaxed" style="color: var(--muted)">{d.summary}</p>
		{/if}

		<!-- Footer: words + status -->
		<div class="mt-2 flex items-center gap-2 text-[11px]" style="color: var(--muted)">
			{#if d.type === 'scene'}<span>{d.words.toLocaleString()} words</span>{/if}
			{#if d.status}
				<span class="rounded border px-1 py-px" style="border-color: var(--border)">{d.status}</span>
			{/if}
		</div>
	</div>

	<!-- Connection handles: target (left), source (right) -->
	<Handle type="target" position={Position.Left} class="!bg-[var(--muted)] !size-2.5" />
	<Handle type="source" position={Position.Right} class="!bg-[var(--muted)] !size-2.5" />
</div>