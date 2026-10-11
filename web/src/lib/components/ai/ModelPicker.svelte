<script lang="ts">
	import { ai } from '#lib/stores/ai.svelte.ts';
</script>

<select
	bind:value={ai.model}
	class="rounded border px-2 py-1 text-xs"
	style="border-color: var(--border); background: var(--surface)"
>
	{#if ai.providerModels[ai.provider]?.length}
		{#each ai.providerModels[ai.provider] as m}
			<option value={m}>{m}</option>
		{/each}
	{:else}
		<option value="">No models loaded</option>
	{/if}
</select>
