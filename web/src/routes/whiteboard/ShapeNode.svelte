<script lang="ts">
	import { Handle, Position, type Node, type NodeProps } from '@xyflow/svelte';
	import { Square, Circle, Triangle, ArrowRight } from '@lucide/svelte';

	type ShapeNodeType = Node<{ label?: string; shape?: string }, 'shape'>;

	let { data, selected }: NodeProps<ShapeNodeType> = $props();

	const shape = $derived(data?.shape || 'rectangle');
	const label = $derived(data?.label || 'Shape');
</script>

<div class="shape-node {selected ? 'selected' : ''}">
	<Handle type="target" position={Position.Left} />
	{#if shape === 'arrow'}
		<ArrowRight size={32} style="color:var(--accent)" />
	{:else if shape === 'circle'}
		<Circle size={32} style="color:var(--accent)" />
	{:else if shape === 'triangle'}
		<Triangle size={32} style="color:var(--accent)" />
	{:else}
		<Square size={32} style="color:var(--accent)" />
	{/if}
	<span class="shape-label">{label}</span>
	<Handle type="source" position={Position.Right} />
</div>

<style>
	:global(.shape-node) {
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
		border-color: var(--accent);
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 30%, transparent);
	}
	.shape-label {
		font-size: .75rem;
		color: var(--text);
		text-align: center;
	}
</style>
