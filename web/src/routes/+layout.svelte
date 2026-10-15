<script lang="ts">
	import './layout.css';
	import favicon from '#lib/assets/favicon.svg';
	import { auth } from '#lib/stores/auth.svelte.ts';
	import { appearance } from '#lib/stores/appearance.svelte.ts';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import Toast from '#lib/components/Toast.svelte';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
	let ready = $state(false);

	// The app is client-only (ssr = false) and renders nothing until the auth check is done,
	// so applying the saved theme here happens before any content is painted.
	appearance.init();

	onMount(async () => {
		if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
		try {
			await auth.refresh();
		} finally {
			ready = true;
		}
	});

	// Route guard: unauthenticated users only ever see /login.
	// /register requires an authenticated session (it creates additional accounts),
	// so it is intentionally excluded here and guards itself.
	$effect(() => {
		if (!ready) return;
		const onAuthPage = page.url.pathname.startsWith('/login');
		if (!auth.status?.authenticated && !onAuthPage) goto('/login');
		else if (auth.status?.authenticated && onAuthPage) goto('/');
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<link rel="manifest" href="/manifest.webmanifest" />
	<meta name="theme-color" content={appearance.active?.window ?? "#14161b"} />
	<title>Moduskript</title>
</svelte:head>

{#if ready}
	<Toast />
	{@render children()}
{/if}
