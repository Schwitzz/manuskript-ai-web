<script lang="ts">
	import { FileText } from '@lucide/svelte';
	import type { OutlineItem, LabelDef } from '#lib/outline';

	let {
		item,
		labels,
		statusList,
		selected,
		onSelect,
		onOpen,
	}: {
		item: OutlineItem;
		labels: LabelDef[];
		statusList: string[];
		selected: boolean;
		onSelect: () => void;
		onOpen: () => void;
	} = $props();

	const d = $derived(item);
		const colour = $derived(labels.find((l) => l.name === d.label)?.color ?? '#94a3b8');
	const colourAlpha = $derived(colour + '20');
	const status = $derived(statusList[parseInt(d.status) - 1] ?? '');

	/** Clamp summary to ~120 chars for the card body. */
	const summary = $derived(
		d.summary_full && d.summary_full.length > 120
			? d.summary_full.slice(0, 120) + '…'
			: d.summary_full || d.summary_sentence || '',
	);

	/** Human-readable word count (e.g. "3.2k"). */
	function fmtWords(w: number): string {
		if (w >= 1000) return `${(w / 1000).toFixed(1)}k`;
		return String(w);
	}
</script>

<div
	class="group relative flex flex-col rounded-lg border bg-card shadow-sm transition-all duration-150"
	role="button"
	tabindex="0"
	style:background={selected ? 'transparent' : undefined}
	style:borderColor={selected ? colour : undefined}
	style:boxShadow={selected ? `0 0 0 2px ${colour}40` : undefined}
	onclick={(e) => { e.stopPropagation(); onSelect(); }}
	onkeydown={(e) => { if (e.key === 'Enter') onSelect(); }}
>
	<!-- Header: number badge + colour stripe + title -->
	<div class="flex items-center gap-2 border-b px-3 py-2">
		<!-- Number badge -->
		<span
			class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold text-white"
			style:background={colour}
			aria-label={`Scene ${item.id}`}
		>
			{item.id}
		</span>

		<!-- Colour stripe -->
		<div class="h-3 w-1 shrink-0 rounded-full" style:background={colour}></div>

		<!-- Title (truncated) -->
		<span class="truncate text-sm font-medium leading-tight">{item.title}</span>

		<!-- Status chip -->
		{#if status}
			<span
				class="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium"
				style={"background:" + colourAlpha + ";color:" + colour}
			>
				{status}
			</span>
		{/if}
	</div>

	<!-- Body: summary -->
	{#if summary}
		<p class="px-3 py-1 text-xs text-muted-foreground line-clamp-3">{summary}</p>
	{/if}

	<!-- Footer: words + Open -->
	<div class="mt-auto flex items-center justify-between border-t px-3 py-2">
		<span class="text-[11px] text-muted-foreground">{fmtWords(item.words)} words</span>
		<button
			type="button"
			class="shrink-0 rounded px-1.5 py-0.5 text-[11px] font-medium"
			style:background={`${colour}15`}
			style:color={colour}
			onclick={(e) => { e.stopPropagation(); onOpen(); }}
		>
			<FileText size={12} /> Open
		</button>
	</div>
</div>
