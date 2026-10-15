<script lang="ts">
	import { Handle, Position, type Node, type NodeProps } from '@xyflow/svelte';
	import { Square, Circle, Triangle, ArrowRight, StickyNote } from '@lucide/svelte';

	type ShapeNodeData = {
		label?: string;
		shape?: string;
		note?: string;
		color?: string;
		showNotes?: boolean;
		onUpdate?: (patch: { label?: string; note?: string; color?: string }) => void;
	};
	type ShapeNodeType = Node<ShapeNodeData, 'shape'>;

	let { data, selected }: NodeProps<ShapeNodeType> = $props();

	const shape = $derived(data?.shape || 'rectangle');
	const label = $derived(data?.label || '');
	const note = $derived(data?.note || '');
	const color = $derived(data?.color || '');
	const showNotes = $derived(Boolean(data?.showNotes));
	const activeColor = $derived(color || 'var(--accent)');

	let editingLabel = $state(false);
	let draftLabel = $state('');

	function startInlineEdit(e: MouseEvent) {
		e.stopPropagation();
		draftLabel = label;
		editingLabel = true;
	}

	function commitInlineEdit() {
		if (!editingLabel) return;
		editingLabel = false;
		const clean = draftLabel.trim() || '';
		data?.onUpdate?.({ label: clean });
	}
</script>

<div
	class="shape-node {selected ? 'selected' : ''}"
	data-color={color || undefined}
	style="--node-color: {activeColor}; {color ? `border-color: ${color}; background: color-mix(in srgb, ${color} 12%, var(--surface));` : ''}"
>
	<Handle type="target" position={Position.Left} />
	{#if note}
		<span class="shape-note-badge" title="Has note" aria-label="Shape has note">
			<StickyNote size={11} />
		</span>
		<div class="shape-note-popover {showNotes ? 'force-visible' : ''}" role="note">
			{note}
		</div>
	{/if}
	{#if shape === 'arrow'}
		<ArrowRight size={32} style="color: {activeColor}" />
	{:else if shape === 'circle'}
		<Circle size={32} style="color: {activeColor}" />
	{:else if shape === 'triangle'}
		<Triangle size={32} style="color: {activeColor}" />
	{:else}
		<Square size={32} style="color: {activeColor}" />
	{/if}
	{#if editingLabel}
		<input
			type="text"
			class="shape-label-input nodrag"
			aria-label="Shape name"
			bind:value={draftLabel}
			onblur={commitInlineEdit}
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => {
				e.stopPropagation();
				if (e.key === 'Enter') commitInlineEdit();
				if (e.key === 'Escape') editingLabel = false;
			}}
		/>
	{:else}
		<span
			class="shape-label"
			ondblclick={startInlineEdit}
			title="Double-click to rename"
			role="button"
			tabindex="0"
		>{label}</span>
	{/if}
	<Handle type="source" position={Position.Right} />
</div>

<style>
	:global(.shape-node) {
		position: relative;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
		padding: 12px 18px;
		border-radius: 8px;
		background: var(--surface);
		border: 1.5px solid var(--border);
		cursor: pointer;
		user-select: none;
		min-width: 84px;
	}
	:global(.shape-node.selected) {
		border-color: var(--node-color, var(--accent));
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--node-color, var(--accent)) 30%, transparent);
	}
	.shape-label {
		font-size: .75rem;
		color: var(--text);
		text-align: center;
		max-width: 140px;
		overflow-wrap: anywhere;
	}
	.shape-label-input {
		width: 96px;
		font-size: .75rem;
		padding: 2px 4px;
		border: 1px solid var(--node-color, var(--accent));
		border-radius: 4px;
		background: var(--bg);
		color: var(--text);
		text-align: center;
	}
	.shape-note-badge {
		position: absolute;
		top: 4px;
		right: 4px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		color: var(--node-color, var(--accent));
		opacity: 0.75;
	}
	.shape-note-popover {
		position: absolute;
		bottom: calc(100% + 6px);
		left: 50%;
		transform: translateX(-50%);
		z-index: 40;
		min-width: 120px;
		max-width: 220px;
		padding: 6px 8px;
		border-radius: 6px;
		background: var(--surface);
		border: 1px solid var(--border);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
		color: var(--text);
		font-size: .7rem;
		line-height: 1.35;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		pointer-events: none;
		opacity: 0;
		visibility: hidden;
		transition: opacity .15s ease, visibility .15s ease;
	}
	:global(.shape-node:hover) .shape-note-popover,
	:global(.shape-node:focus-within) .shape-note-popover,
	.shape-note-popover.force-visible {
		opacity: 1;
		visibility: visible;
	}
</style>
