<script lang="ts">
	import AppShell from '#lib/components/AppShell.svelte';
	import AppearanceSettings from '#lib/components/AppearanceSettings.svelte';
	import { ArrowLeft } from '@lucide/svelte';
	import { goto } from '$app/navigation';
</script>

<AppShell title="Themes">
	<div class="mx-auto flex max-w-3xl flex-col gap-4">
		<div>
			<button
				type="button"
				class="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium"
				style="border-color: var(--border); background: var(--surface); color: var(--text)"
				onclick={() => goto('/more')}
			>
				<ArrowLeft size={14} /> Back to More
			</button>
		</div>
		<AppearanceSettings />
	</div>
</AppShell>
