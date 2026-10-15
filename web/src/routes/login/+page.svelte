<script lang="ts">
	import { api, ApiError } from '#lib/api.ts';
	import { auth } from '#lib/stores/auth.svelte.ts';
	import { BookOpen, UserPlus, LogIn, ShieldCheck } from '@lucide/svelte';
	import { goto } from '$app/navigation';

	let username = $state('');
	let password = $state('');
	let code = $state('');
	let error = $state('');
	let busy = $state(false);
	let manualCreateMode = $state(false);

	const mode = $derived(
		auth.status?.totp_pending
			? 'totp'
			: auth.status?.setup_required || manualCreateMode
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
				const res = await fetch('/api/auth/setup', {
					method: 'POST',
					headers: {
						'content-type': 'application/json',
						'x-allow-local-signup': '1'
					},
					credentials: 'same-origin',
					body: JSON.stringify({ username: cleanUser, password })
				});
				if (!res.ok) {
					let msg = res.statusText;
					try {
						const j = await res.json();
						msg = typeof j.detail === 'string' ? j.detail : msg;
					} catch {}
					throw new ApiError(res.status, msg);
				}
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

	{#if mode !== 'totp' && !auth.status?.setup_required}
		<div class="flex gap-1 rounded-lg border p-1" style="border-color: var(--border); background: var(--surface)">
			<button
				type="button"
				class="flex flex-1 items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-medium"
				style="background: {!manualCreateMode ? 'var(--accent)' : 'transparent'}; color: {!manualCreateMode ? 'var(--accent-text)' : 'var(--text)'}"
				onclick={() => { manualCreateMode = false; error = ''; }}
			>
				<LogIn size={14} /> Sign In
			</button>
			<button
				type="button"
				class="flex flex-1 items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-medium"
				style="background: {manualCreateMode ? 'var(--accent)' : 'transparent'}; color: {manualCreateMode ? 'var(--accent-text)' : 'var(--text)'}"
				onclick={() => { manualCreateMode = true; error = ''; }}
			>
				<UserPlus size={14} /> Create Account
			</button>
		</div>
	{/if}

	<form onsubmit={submit} class="flex flex-col gap-4 rounded-xl border p-5" style="border-color: var(--border); background: var(--surface)">
		<p class="text-sm" style="color: var(--muted)">
			{#if auth.status?.setup_required}Create your account. This only works once.
			{:else if mode === 'setup'}Create a new local account and sign in.
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
					autocomplete="username"
					autocapitalize="off"
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
					autocomplete={mode === 'setup' ? 'new-password' : 'current-password'}
					minlength={mode === 'setup' ? 10 : 1}
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
					autocomplete="one-time-code"
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
