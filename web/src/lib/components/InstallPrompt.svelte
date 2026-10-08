<script lang="ts">
	import { Download } from '@lucide/svelte';
	import { onMount } from 'svelte';

	// Chromium fires beforeinstallprompt; iOS Safari has no such event, so we show a hint.
	interface InstallEvent extends Event {
		prompt(): Promise<void>;
		userChoice: Promise<{ outcome: string }>;
	}

	let deferred = $state<InstallEvent | null>(null);
	let installed = $state(false);
	let ios = $state(false);

	onMount(() => {
		installed =
			window.matchMedia('(display-mode: standalone)').matches ||
			(navigator as unknown as { standalone?: boolean }).standalone === true;
		ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
		const onPrompt = (e: Event) => {
			e.preventDefault();
			deferred = e as InstallEvent;
		};
		const onInstalled = () => (installed = true);
		window.addEventListener('beforeinstallprompt', onPrompt);
		window.addEventListener('appinstalled', onInstalled);
		return () => {
			window.removeEventListener('beforeinstallprompt', onPrompt);
			window.removeEventListener('appinstalled', onInstalled);
		};
	});

	async function install() {
		if (!deferred) return;
		await deferred.prompt();
		await deferred.userChoice;
		deferred = null;
	}
</script>

{#if !installed && (deferred || ios)}
	<section
		class="flex flex-col gap-2 rounded-lg border p-4"
		style="background: var(--surface); border-color: var(--border)"
		aria-label="Install app"
	>
		<h2 class="flex items-center gap-2 font-semibold"><Download size={20} /> Install app</h2>
		{#if deferred}
			<button
				class="rounded-lg px-4 font-medium"
				style="background: var(--accent); color: var(--accent-text)"
				onclick={install}>Add to home screen</button
			>
		{:else}
			<p class="text-sm">
				In Safari, tap the Share button, then choose <strong>Add to Home Screen</strong>.
			</p>
		{/if}
	</section>
{/if}
