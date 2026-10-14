<script lang="ts">
	import { Handle, Position, type Node, type NodeProps } from '@xyflow/svelte';
	import { Flag } from '@lucide/svelte';
	import type { OutlineItem } from '#lib/outline.ts';

	type SceneCardNodeType = Node<{ scene?: OutlineItem }, 'scene'>;

	let { data }: NodeProps<SceneCardNodeType> = $props();

	const scene = $derived(data?.scene);
	const label = $derived(scene?.title || scene?.label || 'Scene');
	const body = $derived(scene?.summary_sentence || '');

	let expanded = $state(false);
</script>

<button type="button" class="scene-card-node" onclick={() => (expanded = !expanded)}>
	<Handle type="target" position={Position.Left} />
	<Handle type="source" position={Position.Right} />
	<div class="scene-card-header">
		<Flag size={16} style="color:var(--accent)" />
		<span class="scene-label">{label}</span>
	</div>
	{#if expanded && body}
		<div class="scene-card-body">
			{body}
		</div>
	{/if}
</button>

<style>
	:global(.scene-card-node) {
		padding: 10px;
		border-radius: 8px;
		background: var(--surface);
		border: 1px solid var(--border);
		cursor: pointer;
		user-select: none;
		min-width: 200px;
		text-align: left;
	}
	:global(.scene-card-node:hover) {
		border-color: var(--accent);
	}
	:global(.scene-card-header) {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.scene-label {
		font-size: .8rem;
		font-weight: 600;
		color: var(--text);
	}
	.scene-card-body {
		margin-top: 6px;
		font-size: .7rem;
		color: var(--muted);
		line-height: 1.4;
		max-height: 80px;
		overflow: hidden;
	}
</style>
