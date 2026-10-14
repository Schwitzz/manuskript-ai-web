<script lang="ts">
	import OutlineNode from './OutlineNode.svelte';
	import { Folder, FileText, ChevronRight, ChevronDown, Pencil, Trash2, StickyNote } from '@lucide/svelte';
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
	data-node={node.id}
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

	{#if node.associated_notes?.length}
		<span
			class="flex shrink-0 items-center gap-0.5 rounded px-1.5 py-0.5 text-xs"
			style="background: var(--surface); color: var(--muted); border: 1px solid var(--border)"
			title="{node.associated_notes.length} associated note{node.associated_notes.length === 1 ? '' : 's'}"
		>
			<StickyNote size={12} />
			{node.associated_notes.length}
		</span>
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

{#if node.associated_notes?.length}
	<div
		class="flex flex-col border-b py-1 pr-3"
		style="border-color: var(--border); padding-left: {40 + depth * 20}px; background: var(--surface)"
	>
		{#each node.associated_notes as n (n.id)}
			<button
				type="button"
				class="flex items-start gap-2 rounded px-2 py-1 text-left text-xs hover:opacity-80"
				onclick={() => onSelect(node)}
			>
				<StickyNote size={13} class="mt-0.5 shrink-0" style="color: var(--accent)" />
				<span class="min-w-0 flex-1">
					<strong class="font-medium" style="color: var(--text)">{n.title}</strong>
					{#if n.text}
						<span class="ml-1 truncate" style="color: var(--muted)">— {n.text}</span>
					{/if}
				</span>
			</button>
		{/each}
	</div>
{/if}

{#if isOpen && node.children.length > 0}
	<div class="outline-children" role="group" data-parent={node.type === 'folder' ? String(node.id) : ''}>
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
	</div>
{/if}
