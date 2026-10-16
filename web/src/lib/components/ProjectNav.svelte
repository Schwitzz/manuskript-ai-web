<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { BookOpen, FileText, GitBranch, Users, Globe, Tag } from '@lucide/svelte';

	let {
		active,
		onSelectSettingsTab
	}: {
		active: 'general' | 'summary' | 'plots' | 'characters' | 'world' | 'labels';
		onSelectSettingsTab?: (tab: 'general' | 'summary') => void;
	} = $props();

	const items = [
		{ id: 'general' as const, label: 'Title Properties', href: '/settings?tab=general', icon: BookOpen },
		{ id: 'summary' as const, label: 'Summary', href: '/settings?tab=summary', icon: FileText },
		{ id: 'plots' as const, label: 'Plot & Subplots', href: '/plots', icon: GitBranch },
		{ id: 'characters' as const, label: 'Characters', href: '/characters', icon: Users },
		{ id: 'world' as const, label: 'World Builder', href: '/world', icon: Globe },
		{ id: 'labels' as const, label: 'Labels & Statuses', href: '/labels', icon: Tag }
	];

	function handleClick(item: (typeof items)[number]) {
		if (
			(item.id === 'general' || item.id === 'summary') &&
			page.url.pathname === '/settings' &&
			onSelectSettingsTab
		) {
			onSelectSettingsTab(item.id);
		} else {
			goto(item.href);
		}
	}
</script>

<div
	class="flex flex-wrap gap-1 rounded-lg border p-1"
	style="border-color: var(--border); background: var(--surface)"
	role="tablist"
	aria-label="Project sections"
>
	{#each items as item (item.id)}
		{@const isCurrent = active === item.id}
		<button
			type="button"
			role="tab"
			aria-selected={isCurrent}
			class="flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors sm:flex-1"
			style="background: {isCurrent ? 'var(--accent)' : 'transparent'}; color: {isCurrent
				? 'var(--accent-text)'
				: 'var(--text)'}"
			onclick={() => handleClick(item)}
		>
			<item.icon size={14} class="shrink-0" />
			<span class="truncate">{item.label}</span>
		</button>
	{/each}
</div>
