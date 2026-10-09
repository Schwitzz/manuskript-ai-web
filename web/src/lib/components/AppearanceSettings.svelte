<script lang="ts">
	import { appearance } from '#lib/stores/appearance.svelte.ts';
	import { SCHEMES, SYSTEM } from '#lib/themes/schemes.ts';
	import { Palette, Check } from '@lucide/svelte';

	const densities = [
		{ id: 'compact', label: 'Compact' },
		{ id: 'comfortable', label: 'Comfortable' },
		{ id: 'spacious', label: 'Spacious' }
	] as const;

	const choices = [
		{ id: SYSTEM, name: 'System', colors: null },
		...SCHEMES.map((s) => ({ id: s.id, name: s.name, colors: s }))
	];

	const field = 'rounded-lg border px-3';
	const fieldStyle = 'background: var(--surface); border-color: var(--border)';
</script>

<section
	class="flex flex-col gap-4 rounded-lg border p-4"
	style="background: var(--surface); border-color: var(--border)"
	aria-label="Appearance"
>
	<h2 class="flex items-center gap-2 font-semibold"><Palette size={20} /> Appearance</h2>

	<div class="flex flex-col gap-2">
		<span class="text-sm" id="theme-label">Theme</span>
		<div class="grid grid-cols-2 gap-2" role="radiogroup" aria-labelledby="theme-label">
			{#each choices as c (c.id)}
				{@const selected = appearance.value.scheme === c.id}
				<button
					type="button"
					role="radio"
					aria-checked={selected}
					data-scheme={c.id}
					class="flex items-center gap-2 rounded-lg border px-2 text-left text-sm"
					style="border-color: {selected ? 'var(--accent)' : 'var(--border)'}; border-width: {selected
						? '2px'
						: '1px'}"
					onclick={() => appearance.set({ scheme: c.id })}
				>
					<span
						class="flex size-6 shrink-0 overflow-hidden rounded-full border"
						style="border-color: var(--border-strong, var(--border))"
						aria-hidden="true"
					>
						{#if c.colors}
							<span class="w-1/2" style="background: {c.colors.window}"></span>
							<span class="w-1/2" style="background: {c.colors.accent}"></span>
						{:else}
							<span class="w-1/2" style="background: #14161b"></span>
							<span class="w-1/2" style="background: #f4f5f7"></span>
						{/if}
					</span>
					<span class="flex-1 py-1 leading-tight">{c.name}</span>
					{#if selected}<Check size={16} />{/if}
				</button>
			{/each}
		</div>
	</div>

	<div class="flex flex-col gap-2">
		<span class="text-sm" id="density-label">Density</span>
		<div class="grid grid-cols-3 gap-1" role="radiogroup" aria-labelledby="density-label">
			{#each densities as d (d.id)}
				{@const on = appearance.value.density === d.id}
				<button
					type="button"
					role="radio"
					aria-checked={on}
					class="rounded-lg border text-sm"
					style="background: {on ? 'var(--accent)' : 'transparent'}; color: {on
						? 'var(--accent-text)'
						: 'inherit'}; border-color: var(--border)"
					onclick={() => appearance.set({ density: d.id })}>{d.label}</button
				>
			{/each}
		</div>
	</div>

	<label class="flex flex-col gap-1">
		<span class="text-sm">Text size: {Math.round(appearance.value.fontScale * 100)}%</span>
		<input
			type="range"
			min="0.85"
			max="1.5"
			step="0.05"
			value={appearance.value.fontScale}
			oninput={(e) => appearance.set({ fontScale: Number(e.currentTarget.value) })}
		/>
	</label>

	<div class="flex items-center gap-3">
		<label class="flex items-center gap-2 text-sm">
			Accent colour
			<input
				type="color"
				class="{field} w-14 p-1"
				style={fieldStyle}
				value={appearance.value.accent ?? appearance.active?.accent ?? '#6ea8fe'}
				oninput={(e) => appearance.set({ accent: e.currentTarget.value })}
			/>
		</label>
		{#if appearance.value.accent}
			<button
				type="button"
				class="rounded-lg border px-3 text-sm"
				style="border-color: var(--border)"
				onclick={() => appearance.set({ accent: null })}>Use theme's</button
			>
		{/if}
	</div>
</section>
