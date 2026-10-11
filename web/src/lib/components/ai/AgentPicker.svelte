<script lang="ts">
	import { ai } from '#lib/stores/ai.svelte.ts';
	import { BrainCircuit } from '@lucide/svelte';
</script>

<div class="flex items-center gap-1">
	<BrainCircuit size={14} style="color: var(--muted)" />
	<select
		bind:value={ai.agent}
		class="rounded border px-2 py-1 text-xs"
		style="border-color: var(--border); background: var(--surface)"
	>
		{#each ai.agents as a}
			<option value={a.name}>{a.name}</option>
		{/each}
	</select>
</div>
