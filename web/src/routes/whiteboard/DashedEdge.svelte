<script lang="ts">
	import { getBezierPath } from '@xyflow/system';
	import { type EdgeProps } from '@xyflow/svelte';
	import { LINE_TYPES } from '#lib/whiteboard/line-types';

	let {
		id,
		sourceX,
		sourceY,
		targetX,
		targetY,
		sourcePosition,
		targetPosition,
		markerStart,
		markerEnd,
		interactionWidth = 20,
		data
	}: EdgeProps = $props();

	const [path] = $derived(
		getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition })
	);

	const dash = $derived(
		(LINE_TYPES.find((t) => t.id === data?.lineType) ?? LINE_TYPES[0])?.dasharray ?? ''
	);
</script>

<path
	{id}
	d={path}
	class="svelte-flow__edge-path"
	marker-start={markerStart}
	marker-end={markerEnd}
	fill="none"
	stroke="var(--accent, #3b82f6)"
	stroke-width="2"
	stroke-dasharray={dash || undefined}
	style="stroke: var(--accent, #3b82f6); stroke-width: 2px;{dash ? ` stroke-dasharray: ${dash};` : ''}"
/>
{#if interactionWidth && interactionWidth > 0}
	<path
		d={path}
		stroke-opacity={0}
		stroke-width={interactionWidth}
		fill="none"
		class="svelte-flow__edge-interaction"
	/>
{/if}
