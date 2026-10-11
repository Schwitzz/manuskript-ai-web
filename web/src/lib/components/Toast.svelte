<script lang="ts">
	import { toastStore, removeToast } from '#lib/stores/toast.svelte.ts';

	const store = toastStore();
</script>

<div class="fixed bottom-20 left-1/2 z-50 flex -translate-x-1/2 flex-col gap-2" style="max-width: 90vw;">
	{#each store.get() as toast (toast.id)}
		<div
			class="flex items-center gap-3 rounded-lg border px-4 py-3 shadow-lg"
			style="background: var(--surface); border-color: var(--border)"
			role="alert"
		>
			<span class="text-sm flex-1">{toast.message}</span>
			{#if toast.actionLabel}
				<button
					class="rounded px-2 py-1 text-sm font-medium"
					style="background: var(--accent); color: var(--accent-text)"
					onclick={() => { toast.onAction?.(); removeToast(toast.id); }}
				>
					{toast.actionLabel}
				</button>
			{/if}
			<button
				class="rounded p-1"
				style="color: var(--muted)"
				onclick={() => removeToast(toast.id)}
			>
				&#x2715;
			</button>
		</div>
	{/each}
</div>
