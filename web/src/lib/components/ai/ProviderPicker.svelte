<script lang="ts">
	import { ai } from '#lib/stores/ai.svelte.ts';

	function onChange(e: Event) {
		const val = (e.target as HTMLSelectElement).value;
		ai.provider = val;
		ai.reloadModels();
	}
</script>

<select
	bind:value={ai.provider}
	onchange={onChange}
	class="rounded border px-2 py-1 text-xs"
	style="border-color: var(--border); background: var(--surface)"
>
	{#each ai.availableProviders as p}
		<option value={p}>{p}</option>
	{/each}
</select>
