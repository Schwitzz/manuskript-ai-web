<script lang="ts">
	import { Handle, Position, type Node, type NodeProps } from '@xyflow/svelte';

	type NoteNodeType = Node<{ text?: string }, 'note'>;

	let { data, selected }: NodeProps<NoteNodeType> = $props();
	const text = $derived(data?.text || 'Note');
</script>

<div
	class="note-node {selected ? 'selected' : ''}"
	role="textbox"
	tabindex="0"
	contenteditable="true"
	onkeydown={(e) => e.key === 'Enter' && e.preventDefault()}
>
	<Handle type="target" position={Position.Left} />
	<span class="note-text">{text}</span>
	<Handle type="source" position={Position.Right} />
</div>

<style>
	:global(.note-node) {
		padding: 12px 16px;
		border-radius: 8px;
		background: var(--surface);
		border: 1.5px solid var(--border);
		cursor: pointer;
		user-select: none;
		min-width: 120px;
	}
	:global(.note-node.selected),
	:global(.note-node:focus-within) {
		border-color: var(--accent);
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 30%, transparent);
	}
	.note-text {
		font-size: .85rem;
		color: var(--text);
		line-height: 1.4;
		outline: none;
	}
</style>
