<script lang="ts">
	import { api, ApiError } from '#lib/api.ts';
	import { auth } from '#lib/stores/auth.svelte.ts';
	import { BookOpen } from '@lucide/svelte';

	let username = $state('');
	let password = $state('');
	let code = $state('');
	let error = $state('');
	let busy = $state(false);

	const mode = $derived(
		auth.status?.setup_required ? 'setup' : auth.status?.totp_pending ? 'totp' : 'login'
	);

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		error = '';
		busy = true;
		try {
			if (mode === 'setup') {
				await api('POST', '/api/auth/setup', { username, password });
			} else if (mode === 'totp') {
				await api('POST', '/api/auth/totp/verify', { code });
			} else {
				await api('POST', '/api/auth/login', { username, password });
			}
			await auth.refresh();
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
		<h1 class="text-2xl font-semibold">Manuskript AI</h1>
	</div>

	<form onsubmit={submit} class="flex flex-col gap-4">
		<p style="color: var(--muted)">
			{#if mode === 'setup'}Create your account. This only works once.
			{:else if mode === 'totp'}Enter the 6-digit code from your authenticator app, or a recovery code.
			{:else}Log in to continue.{/if}
		</p>

		{#if mode !== 'totp'}
			<label class="flex flex-col gap-1">
				<span class="text-sm">Username</span>
				<input
					class="rounded-lg border px-3"
					style="background: var(--surface); border-color: var(--border)"
					bind:value={username}
					autocomplete="username"
					autocapitalize="off"
					required
				/>
			</label>
			<label class="flex flex-col gap-1">
				<span class="text-sm">Password{mode === 'setup' ? ' (at least 10 characters)' : ''}</span>
				<input
					class="rounded-lg border px-3"
					style="background: var(--surface); border-color: var(--border)"
					type="password"
					bind:value={password}
					autocomplete={mode === 'setup' ? 'new-password' : 'current-password'}
					minlength={mode === 'setup' ? 10 : 1}
					required
				/>
			</label>
		{:else}
			<label class="flex flex-col gap-1">
				<span class="text-sm">Code</span>
				<input
					class="rounded-lg border px-3"
					style="background: var(--surface); border-color: var(--border)"
					bind:value={code}
					inputmode="numeric"
					autocomplete="one-time-code"
					required
				/>
			</label>
		{/if}

		{#if error}
			<p role="alert" style="color: var(--danger)">{error}</p>
		{/if}

		<button
			class="rounded-lg px-4 font-medium disabled:opacity-60"
			style="background: var(--accent); color: var(--accent-text)"
			disabled={busy}
		>
			{mode === 'setup' ? 'Create account' : mode === 'totp' ? 'Verify' : 'Log in'}
		</button>
	</form>
</main>
