<script lang="ts">
	import { api, ApiError } from '#lib/api.ts';
	import { auth } from '#lib/stores/auth.svelte.ts';
	import { BookOpen, ShieldCheck } from '@lucide/svelte';
	import { goto } from '$app/navigation';

	let username = $state('');
	let password = $state('');
	let code = $state('');
	let error = $state('');
	let busy = $state(false);

	const mode = $derived(
		auth.status?.totp_pending
			? 'totp'
			: auth.status?.setup_required
				? 'setup'
				: 'login'
	);

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		error = '';
		const cleanUser = username.trim();
		if (mode !== 'totp' && !cleanUser) {
			error = 'Username is required';
			return;
		}
		if (mode === 'setup' && password.length < 10) {
			error = 'Password must be at least 10 characters';
			return;
		}
		busy = true;
		try {
			if (mode === 'setup') {
				await api('POST', '/api/auth/setup', { username: cleanUser, password });
			} else if (mode === 'totp') {
				await api('POST', '/api/auth/totp/verify', { code });
			} else {
				await api('POST', '/api/auth/login', { username: cleanUser, password });
			}
			const st = await auth.refresh();
			if (st?.authenticated) {
				await goto('/write', { replaceState: true });
			}
		} catch (err: unknown) {
			error = err instanceof ApiError ? err.message : 'Could not reach the server';
		} finally {
			busy = false;
		}
	}
</script>

<main class="mx-auto flex min-h-dvh max-w-sm flex-col justify-center gap-6 px-5 py-8">
	<div class="flex items-center gap-3">
		<BookOpen size={32} color="var(--accent)" />
		<div>
			<h1 class="text-2xl font-semibold">Moduskript</h1>
			<p class="text-xs" style="color: var(--muted)">Writing Studio & Web Sync</p>
		</div>
	</div>

	<form onsubmit={submit} class="flex flex-col gap-4 rounded-xl border p-5" style="border-color: var(--border); background: var(--surface)" novalidate>
		<p class="text-sm" style="color: var(--muted)">
			{#if mode === 'setup'}Welcome to Moduskript! Create your primary account. This only works once.
			{:else if mode === 'totp'}Enter the 6-digit code from your authenticator app, or a recovery code.
			{:else}Log in to continue.{/if}
		</p>

		{#if mode !== 'totp'}
			<label class="flex flex-col gap-1">
				<span class="text-sm font-medium">Username</span>
				<input
					class="rounded-lg border px-3 py-2"
					style="background: var(--bg); border-color: var(--border); color: var(--text)"
					bind:value={username}
					autocomplete="off"
					autocapitalize="off"
					spellcheck="false"
					required
				/>
			</label>
			<label class="flex flex-col gap-1">
				<span class="text-sm font-medium">Password{mode === 'setup' ? ' (at least 10 characters)' : ''}</span>
				<input
					class="rounded-lg border px-3 py-2"
					style="background: var(--bg); border-color: var(--border); color: var(--text)"
					type="password"
					bind:value={password}
					autocomplete="off"
					required
				/>
			</label>
		{:else}
			<label class="flex flex-col gap-1">
				<span class="flex items-center gap-1.5 text-sm font-medium"><ShieldCheck size={16} /> Code</span>
				<input
					class="rounded-lg border px-3 py-2"
					style="background: var(--bg); border-color: var(--border); color: var(--text)"
					bind:value={code}
					inputmode="numeric"
					autocomplete="off"
					required
				/>
			</label>
		{/if}

		{#if error}
			<p role="alert" class="text-sm" style="color: var(--danger)">{error}</p>
		{/if}

		<button
			class="rounded-lg px-4 py-2.5 font-medium disabled:opacity-60"
			style="background: var(--accent); color: var(--accent-text)"
			disabled={busy}
		>
			{mode === 'setup' ? 'Create account' : mode === 'totp' ? 'Verify' : 'Log in'}
		</button>
	</form>
</main>
