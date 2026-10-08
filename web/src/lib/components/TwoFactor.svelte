<script lang="ts">
	import { api, ApiError } from '#lib/api.ts';
	import { ShieldCheck } from '@lucide/svelte';
	import { onMount } from 'svelte';

	let enabled = $state(false);
	let step = $state<'idle' | 'enrol' | 'codes' | 'disable'>('idle');
	let secret = $state('');
	let qr = $state('');
	let code = $state('');
	let recovery = $state<string[]>([]);
	let error = $state('');
	let busy = $state(false);

	onMount(async () => {
		enabled = (await api<{ totp_enabled: boolean }>('GET', '/api/auth/me')).totp_enabled;
	});

	async function run(fn: () => Promise<void>) {
		error = '';
		busy = true;
		try {
			await fn();
		} catch (e: unknown) {
			error = e instanceof ApiError ? e.message : 'Could not reach the server';
		} finally {
			busy = false;
		}
	}

	const start = () =>
		run(async () => {
			const r = await api<{ secret: string; qr_svg_base64: string }>('POST', '/api/auth/totp/setup');
			secret = r.secret;
			qr = 'data:image/svg+xml;base64,' + r.qr_svg_base64;
			code = '';
			step = 'enrol';
		});

	const enable = () =>
		run(async () => {
			const r = await api<{ recovery_codes: string[] }>('POST', '/api/auth/totp/enable', { code });
			recovery = r.recovery_codes;
			enabled = true;
			step = 'codes';
			code = '';
		});

	const disable = () =>
		run(async () => {
			await api('POST', '/api/auth/totp/disable', { code });
			enabled = false;
			step = 'idle';
			code = '';
		});

	const field = 'rounded-lg border px-3 w-full';
	const fieldStyle = 'background: var(--surface); border-color: var(--border)';
	const btn = 'rounded-lg px-4 font-medium disabled:opacity-60';
</script>

<section
	class="flex flex-col gap-3 rounded-lg border p-4"
	style="background: var(--surface); border-color: var(--border)"
	aria-label="Two-factor authentication"
>
	<h2 class="flex items-center gap-2 font-semibold">
		<ShieldCheck size={20} /> Two-factor login
		<span class="text-sm font-normal" style="color: var(--muted)">{enabled ? 'On' : 'Off'}</span>
	</h2>

	{#if step === 'idle'}
		{#if enabled}
			<button class={btn} style="border: 1px solid var(--border)" onclick={() => (step = 'disable')}>
				Turn off
			</button>
		{:else}
			<button
				class={btn}
				style="background: var(--accent); color: var(--accent-text)"
				disabled={busy}
				onclick={start}>Set up</button
			>
		{/if}
	{:else if step === 'enrol'}
		<p class="text-sm">Scan this with your authenticator app, then enter the 6-digit code.</p>
		<img src={qr} alt="Two-factor QR code" class="mx-auto size-48 rounded bg-white p-2" />
		<p class="text-center text-xs break-all" style="color: var(--muted)">
			Or type this key: <code>{secret}</code>
		</p>
		<input class={field} style={fieldStyle} bind:value={code} inputmode="numeric"
			autocomplete="one-time-code" aria-label="Code" />
		<button class={btn} style="background: var(--accent); color: var(--accent-text)"
			disabled={busy} onclick={enable}>Turn on</button>
	{:else if step === 'codes'}
		<p class="text-sm">
			Save these recovery codes now. Each works once, and they will not be shown again.
		</p>
		<ul class="grid grid-cols-2 gap-1 font-mono text-sm" aria-label="Recovery codes">
			{#each recovery as c (c)}<li>{c}</li>{/each}
		</ul>
		<button class={btn} style="background: var(--accent); color: var(--accent-text)"
			onclick={() => { step = 'idle'; recovery = []; }}>I have saved them</button>
	{:else}
		<p class="text-sm">Enter a current code to turn two-factor login off.</p>
		<input class={field} style={fieldStyle} bind:value={code} inputmode="numeric"
			autocomplete="one-time-code" aria-label="Code" />
		<div class="flex gap-2">
			<button class={btn} style="border: 1px solid var(--border)"
				onclick={() => { step = 'idle'; error = ''; }}>Cancel</button>
			<button class={btn} style="background: var(--danger); color: var(--accent-text)"
				disabled={busy} onclick={disable}>Turn off</button>
		</div>
	{/if}

	{#if error}<p role="alert" style="color: var(--danger)">{error}</p>{/if}
</section>
