<script lang="ts" generics="T">
	import { Handle, Position } from '@xyflow/svelte';
	import { FileText, Folder, X } from '@lucide/svelte';

	let {
		data,
		selected,
		onSelect,
		onRemove,
		onRename,
		onOpenInEditor,
	}: {
		data: T;
		selected: boolean;
		onSelect: () => void;
		onRemove: () => void;
		onRename: (title: string) => void;
		onOpenInEditor: () => void;
	} = $props();

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

	let editing = $state(false);
	let title = $state('');

	$effect(() => { title = (data as any).title; });

	function saveTitle() {
		if (editing) {
			editing = false;
			onRename(title);
		}
	}
</script>

<div
	class="group relative w-72 rounded-lg border shadow-sm transition-all duration-150"
	role="button"
	tabindex="0"
	onclick={(e) => { e.stopPropagation(); onSelect(); }}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); onSelect(); }
	}}
	style="background: var(--surface);
		border-color: {selected ? 'var(--accent)' : (d.color || 'var(--border)')};
		{selected ? 'box-shadow: 0 0 0 2px var(--accent)/25%' : 'box-shadow: var(--shadow-sm)'}"
>
	<!-- Selection ring (always visible when selected) -->
	{#if selected}
		<div class="absolute inset-0 rounded-lg border-2 pointer-events-none"
			style="border-color: var(--accent)"></div>
	{/if}

	<!-- Label color bar -->
	{#if d.color}
	<div class="h-1.5 rounded-t-lg" style="background: {d.color}"></div>
	{/if}

	<!-- Header row: title + delete -->
	<div class="flex items-center justify-between gap-2 px-3 pt-2">
		{#if editing}
			<input
				class="min-w-0 flex-1 rounded border bg-transparent px-1 py-px text-sm font-medium"
				style="border-color: var(--accent)"
				bind:value={title}
				onblur={saveTitle}
				onkeydown={(e) => {
					e.stopPropagation();
					if (e.key === 'Enter') saveTitle();
					if (e.key === 'Escape') { editing = false; title = d.title; }
				}}
			/>
		{:else}
			<div class="flex items-center gap-1.5 min-w-0 flex-1">
				{#if d.type === 'folder'}
					<Folder size={14} style="color: var(--muted)" />
				{:else}
					<FileText size={14} style="color: var(--muted)" />
				{/if}
				<span class="min-w-0 flex-1 truncate text-sm font-medium">{d.title}</span>
			</div>
		{/if}

		<!-- Delete button (visible on hover or when selected) -->
		<button
			class="tap flex size-5 shrink-0 items-center justify-center rounded opacity-0 transition-opacity hover:opacity-100"
			style="background:var(--surface); border:1px solid var(--border)"
			onclick={(e) => { e.stopPropagation(); onRemove(); }}
			title="Remove"
			type="button"
		>
			<X size={12} style="color: var(--muted)" />
		</button>
	</div>

	<!-- Summary -->
	{#if d.summary}
		<p class="px-3 pb-1 line-clamp-3 text-xs leading-relaxed" style="color: var(--muted)">
			{d.summary}
		</p>
	{/if}

	<!-- Footer: words + status -->
	<div class="flex items-center gap-2 px-3 pb-3 pt-1 text-[11px]" style="color: var(--muted)">
		{#if d.type !== 'folder'}
			<span>{d.words.toLocaleString()} words</span>
		{/if}
		{#if d.status}
			<span class="rounded border px-1 py-px" style="border-color: var(--border)">{d.status}</span>
		{/if}
		{#if d.type !== 'folder'}
			<button
				class="ml-auto text-xs underline"
				onclick={(e) => { e.stopPropagation(); onOpenInEditor(); }}
				type="button"
			>Open</button
			>
		{/if}
	</div>

	<!-- Connection handles: target (left), source (right) — larger, always visible -->
	<Handle
		type="target" position={Position.Left}
		class="!bg-[var(--accent)] !size-3 rounded-full !ring-2 !ring-[var(--surface)]"
	/>
	<Handle
		type="source" position={Position.Right}
		class="!bg-[var(--accent)] !size-3 rounded-full !ring-2 !ring-[var(--surface)]"
	/>
</div>
