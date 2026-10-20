<script lang="ts">
	import { page } from '$app/state';
	import { PenLine, ListTree, Layers, Users, Menu, Sparkles } from '@lucide/svelte';
	import type { Snippet } from 'svelte';
	import { ai } from '#lib/stores/ai.svelte.ts';
	import AIChatPanel from '#lib/components/ai/AIChatPanel.svelte';
	import { onMount } from 'svelte';

	let {
		title,
		headerContent,
		fullHeight = false,
		children
	}: {
		title: string;
		headerContent?: Snippet;
		fullHeight?: boolean;
		children: Snippet;
	} = $props();

	let aiWidth = $state(380);
	let resizing = $state(false);

	onMount(() => {
		try {
			const saved = Number(localStorage.getItem('msk_ai_width'));
			if (saved >= 260 && saved <= 680) aiWidth = saved;
		} catch {}
	});

	function startResize(e: PointerEvent) {
		e.preventDefault();
		resizing = true;
		const onMove = (ev: PointerEvent) => {
			const next = Math.max(260, Math.min(680, window.innerWidth - ev.clientX));
			aiWidth = next;
		};
		const onUp = () => {
			resizing = false;
			try {
				localStorage.setItem('msk_ai_width', String(aiWidth));
			} catch {}
			window.removeEventListener('pointermove', onMove);
			window.removeEventListener('pointerup', onUp);
		};
		window.addEventListener('pointermove', onMove);
		window.addEventListener('pointerup', onUp);
	}

	const tabs = [
		{ href: '/write', label: 'Write', icon: PenLine },
		{ href: '/outline', label: 'Outline', icon: ListTree },
		{ href: '/whiteboard', label: 'Board', icon: Layers },
		{ href: '/characters', label: 'Characters', icon: Users },
		{ href: '/more', label: 'More', icon: Menu }
	];
</script>

<div class="flex h-dvh w-full flex-col overflow-hidden">
	<header
		class="z-10 flex h-14 shrink-0 items-center gap-3 border-b px-4"
		style="background: var(--surface); border-color: var(--border)"
	>
		<div class="flex min-w-0 flex-1 items-center gap-2">
			{#if headerContent}
				{@render headerContent()}
			{:else}
				<h1 class="truncate text-lg font-semibold">{title}</h1>
			{/if}
		</div>
		<button
			class="rounded p-2"
			onclick={() => {
				ai.panelOpen = !ai.panelOpen;
				if (!ai.initialized) ai.init();
			}}
			title="AI Chat"
			aria-label="AI Chat"
			aria-pressed={ai.panelOpen}
		>
			<Sparkles size={20} style="color: {ai.panelOpen ? 'var(--accent)' : 'var(--muted)'}" />
		</button>
	</header>

	<div class="flex min-h-0 flex-1 overflow-hidden">
		<div
			class="min-h-0 min-w-0 flex-1 {fullHeight
				? 'flex flex-col overflow-hidden'
				: 'overflow-y-auto px-4 py-4'}"
		>
			{@render children()}
		</div>

		{#if ai.panelOpen}
			<aside
				class="relative flex h-full shrink-0 border-l"
				style="width: min({aiWidth}px, 85vw); border-color: var(--border); background: var(--surface)"
				aria-label="AI Chat Panel"
			>
				<!-- Resize drag handle -->
				<div
					role="separator"
					aria-orientation="vertical"
					aria-label="Resize AI Chat panel"
					onpointerdown={startResize}
					class="w-1.5 shrink-0 cursor-col-resize transition-colors hover:bg-[var(--accent)]"
					style="background: {resizing ? 'var(--accent)' : 'transparent'}"
					title="Drag to resize AI Chat"
				></div>
				<div class="flex min-w-0 flex-1 flex-col overflow-hidden">
					<AIChatPanel />
				</div>
			</aside>
		{/if}
	</div>

	<nav
		class="z-10 grid shrink-0 grid-cols-5 border-t pb-[env(safe-area-inset-bottom)]"
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
