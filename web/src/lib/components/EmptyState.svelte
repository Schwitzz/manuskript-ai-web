<script lang="ts">
	import type { Snippet } from 'svelte';

	let { title, description, children }: { title: string; description?: string; children?: Snippet } = $props();
</script>

<div class="flex flex-col items-center justify-center gap-2 py-16 text-center">
	{#if children}
		{@render children()}
	{:else}
		<p style="color: var(--muted)">{title}</p>
	{/if}
	{#if description}
		<p class="text-sm" style="color: var(--muted)">{description}</p>
	{/if}
</div>
