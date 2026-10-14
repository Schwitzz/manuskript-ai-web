<script lang="ts">
	import { Handle, Position, type Node, type NodeProps } from '@xyflow/svelte';
	import {
		Sparkles, Type, Notebook, Scissors, Layers, Link, Map, Book, Flag,
		Eye, Clock, Compass, Globe, Mountain, Sun, Cloud, Wind, Flame,
		Droplets, Trash2, Plus, Square, Circle, Triangle, ArrowRight
	} from '@lucide/svelte';

	type IconNodeType = Node<{ label?: string; icon?: string }, 'icon'>;

	let { data, selected }: NodeProps<IconNodeType> = $props();

	const map: Record<string, typeof Sparkles> = {
		Sparkles, Type, Notebook, Scissors, Layers, Link,
		Map, Book, Flag, Eye, Clock, Compass, Globe,
		Mountain, Sun, Cloud, Wind, Flame, Droplets,
		Trash2, Plus, Square, Circle, Triangle, ArrowRight
	};

	const icon = $derived(data?.icon || 'Sparkles');
	const label = $derived(data?.label || icon);
	const IconComp = $derived(map[icon] || Sparkles);
</script>

<div class="icon-node {selected ? 'selected' : ''}">
	<Handle type="target" position={Position.Left} />
	<IconComp size={24} style="color:var(--accent)" />
	<span class="icon-label">{label}</span>
	<Handle type="source" position={Position.Right} />
</div>

<style>
	:global(.icon-node) {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
		padding: 10px 16px;
		border-radius: 8px;
		background: var(--surface);
		border: 1.5px solid var(--border);
		cursor: pointer;
		user-select: none;
		min-width: 76px;
	}
	:global(.icon-node.selected) {
		border-color: var(--accent);
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 30%, transparent);
	}
	.icon-label {
		font-size: .7rem;
		color: var(--muted);
		text-align: center;
	}
</style>
