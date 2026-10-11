<script lang="ts">
	import { goto } from '$app/navigation';
</script>

<div class="flex flex-col items-center justify-center gap-4 py-16 text-center">
	<p style="color: var(--muted)">No project selected.</p>
	<button
		class="rounded-lg px-4 py-2 text-sm font-medium"
		style="background: var(--accent); color: var(--accent-text)"
		onclick={() => goto('/more')}>Choose or create a project</button
	>
</div>
