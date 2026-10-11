<script lang="ts">
	import { page } from '$app/state';
	import { PenLine, ListTree, LayoutGrid, Users, Menu, Sparkles } from '@lucide/svelte';
	import type { Snippet } from 'svelte';
	import { ai } from '#lib/stores/ai.svelte.ts';

	let { title, children }: { title: string; children: Snippet } = $props();

	const tabs = [
		{ href: '/write', label: 'Write', icon: PenLine },
		{ href: '/outline', label: 'Outline', icon: ListTree },
		{ href: '/cards', label: 'Cards', icon: LayoutGrid },
		{ href: '/characters', label: 'Characters', icon: Users },
		{ href: '/more', label: 'More', icon: Menu }
	];
</script>

<div class="flex min-h-dvh flex-col">
	<header
		class="sticky top-0 z-10 flex h-14 items-center border-b px-4"
		style="background: var(--surface); border-color: var(--border)"
	>
		<h1 class="flex-1 text-lg font-semibold">{title}</h1>
		<button
			class="rounded p-2"
			onclick={() => { ai.panelOpen = !ai.panelOpen; if (!ai.initialized) ai.init(); }}
			title="AI Chat"
		>
			<Sparkles size={20} style="color: {ai.panelOpen ? 'var(--accent)' : 'var(--muted)'}" />
		</button>
	</header>

	<div class="flex-1 px-4 py-4">
		{@render children()}
	</div>

	<nav
		class="sticky bottom-0 z-10 grid grid-cols-5 border-t pb-[env(safe-area-inset-bottom)]"
		style="background: var(--surface); border-color: var(--border)"
		aria-label="Main"
	>
		{#each tabs as t (t.href)}
			{@const active = page.url.pathname.startsWith(t.href)}
			<a
				href={t.href}
				class="tap flex min-h-14 flex-col items-center justify-center gap-0.5 text-xs"
				style="color: {active ? 'var(--accent)' : 'var(--muted)'}"
				aria-current={active ? 'page' : undefined}
			>
				<t.icon size={22} />
				<span>{t.label}</span>
			</a>
		{/each}
	</nav>
</div>
