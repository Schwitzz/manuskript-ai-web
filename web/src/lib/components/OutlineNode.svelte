<script lang="ts">
	import OutlineNode from './OutlineNode.svelte';
	import { Folder, FileText, ChevronRight, ChevronDown, Pencil, Trash2 } from '@lucide/svelte';
	import { labelColor, type LabelDef, type OutlineItem } from '#lib/outline.ts';

	let {
		node,
		depth = 0,
		expanded,
		selectedId,
		editingId,
		editingTitle,
		labels,
		statusList,
		onToggleExpand,
		onSelect,
		onRenameStart,
		onRename,
		onRenameCancel,
		onDelete
	}: {
		node: OutlineItem;
		depth?: number;
		expanded: { has(id: string): boolean };
		selectedId: number | null;
		editingId: number | null;
		editingTitle: string;
		labels: LabelDef[];
		statusList: string[];
		onToggleExpand: (id: number) => void;
		onSelect: (node: OutlineItem) => void;
		onRenameStart: (node: OutlineItem) => void;
		onRename: (id: number, title: string) => void;
		onRenameCancel: () => void;
		onDelete: (id: number) => void;
	} = $props();

	let localTitle = $state('');
	$effect(() => {
		localTitle = editingTitle;
	});

	const isOpen = $derived(expanded.has(String(node.id)));
	const color = $derived(labelColor(labels, node.label));
	const statusName = $derived(node.status ? (statusList[Number(node.status) - 1] ?? '') : '');
	function focusOnMount(el: HTMLInputElement) {
		el.focus();
		el.select();
	}
</script>

<div
	role="treeitem"
	aria-selected={selectedId === node.id}
	aria-expanded={node.children.length > 0 ? isOpen : undefined}
	tabindex="0"
	class="flex items-center gap-1 border-b py-1 pr-2 transition-colors"
	style="border-color: var(--border); padding-left: {8 + depth * 20}px; background: {selectedId === node.id ? 'var(--accent)' : 'transparent'}; color: {selectedId === node.id ? 'var(--accent-text)' : 'inherit'}"
	onclick={() => onSelect(node)}
	onkeydown={(e) => {
		if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) {
			e.preventDefault();
			onSelect(node);
		}
	}}
>
	{#if node.children.length > 0}
		<button
			class="tap flex size-8 shrink-0 items-center justify-center"
			onclick={(e) => {
				e.stopPropagation();
				onToggleExpand(node.id);
			}}
			aria-label={isOpen ? 'Collapse' : 'Expand'}
			type="button"
		>
			{#if isOpen}<ChevronDown size={16} />{:else}<ChevronRight size={16} />{/if}
		</button>
	{:else}
		<span class="size-8 shrink-0"></span>
	{/if}

	{#if node.type === 'folder'}
		<Folder size={16} style="color: var(--muted)" />
	{:else}
		<FileText size={16} style="color: var(--muted)" />
	{/if}

	{#if editingId === node.id}
		<input
			class="min-w-0 flex-1 rounded border bg-transparent px-1 text-sm"
			style="border-color: var(--border)"
			aria-label="Title"
			bind:value={localTitle}
			use:focusOnMount
			onblur={() => onRename(node.id, localTitle)}
			onkeydown={(e) => {
				e.stopPropagation();
				if (e.key === 'Enter') onRename(node.id, localTitle);
				if (e.key === 'Escape') onRenameCancel();
			}}
			onclick={(e) => e.stopPropagation()}
		/>
	{:else}
		<span class="min-w-0 flex-1 truncate text-sm">{node.title}</span>
	{/if}

	{#if color}
		<span class="size-2.5 shrink-0 rounded-full" style="background-color: {color}" aria-hidden="true"></span>
	{/if}
	{#if statusName}
		<span class="shrink-0 text-xs" style="opacity: 0.7">{statusName}</span>
	{/if}

	<button
		class="tap flex size-8 shrink-0 items-center justify-center"
		onclick={(e) => {
			e.stopPropagation();
			onRenameStart(node);
		}}
		aria-label="Rename {node.title}"
		type="button"><Pencil size={14} /></button
	>
	<button
		class="tap flex size-8 shrink-0 items-center justify-center"
		onclick={(e) => {
			e.stopPropagation();
			onDelete(node.id);
		}}
		aria-label="Delete {node.title}"
		type="button"
		style="color: var(--danger)"><Trash2 size={14} /></button
	>
</div>

{#if isOpen}
	{#each node.children as child (child.id)}
		<OutlineNode
			node={child}
			depth={depth + 1}
			{expanded}
			{selectedId}
			{editingId}
			{editingTitle}
			{labels}
			{statusList}
			{onToggleExpand}
			{onSelect}
			{onRenameStart}
			{onRename}
			{onRenameCancel}
			{onDelete}
		/>
	{/each}
{/if}
