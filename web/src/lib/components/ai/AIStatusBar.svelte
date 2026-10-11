<script lang="ts">
	import { ai } from '#lib/stores/ai.svelte.ts';
	import { X, Sparkles, Zap } from '@lucide/svelte';
</script>

{#if ai.streaming.isStreaming}
	<div class="flex items-center gap-2 border-t px-3 py-2 text-xs" style="border-color: var(--border)">
		<span class="flex items-center gap-1" style="color: var(--muted)">
			<Sparkles size={14} class="animate-pulse" style="color: var(--accent)" />
			{ai.streaming.thinkingText && !ai.streaming.currentText ? `Thinking... (${ai.streaming.thinkingText.length.toLocaleString()} characters)` : 'Writing...'}
		</span>
		{#if ai.streaming.inTokens || ai.streaming.outTokens}
			<span class="flex items-center gap-1" style="color: var(--muted)">
				<Zap size={12} />
				{ai.streaming.inTokens ?? '?'}in / {ai.streaming.outTokens ?? '?'}out
			</span>
		{/if}
		{#if ai.tokensPerSecond}
			<span style="color: var(--muted)">{ai.tokensPerSecond}/s</span>
		{/if}
		<span style="color: var(--muted)">{ai.elapsedSeconds}s</span>
		<button
			class="ml-auto rounded p-1"
			onclick={() => ai.cancel()}
			title="Cancel"
		>
			<X size={14} style="color: var(--muted)" />
		</button>
	</div>
{/if}
