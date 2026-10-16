<script lang="ts">
	import { ai } from '#lib/stores/ai.svelte.ts';

	let options = $derived(ai.modelsForProvider(ai.provider));
</script>

<select
	bind:value={ai.model}
	aria-label="Select AI Model"
	class="max-w-[160px] truncate rounded border px-2 py-1 text-xs"
	style="border-color: var(--border); background: var(--surface); color: var(--text)"
>
	{#if options.length > 0}
		{#each options as m (m)}
			<option value={m}>{m}</option>
		{/each}
	{:else}
		<option value="">Select model...</option>
	{/if}
</select>
