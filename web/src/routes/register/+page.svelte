<script lang="ts">
	import { api, ApiError, call } from '#lib/api.ts';
	import { auth } from '#lib/stores/auth.svelte.ts';
	import { BookOpen, Users, ShieldCheck } from '@lucide/svelte';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import type { UserRef } from '#lib/api-types.ts';

	let username = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let error = $state('');
	let busy = $state(false);
	let users = $state<UserRef[]>([]);
	let usersError = $state('');

	// Creating a user requires an authenticated session (admin-only action).
	onMount(async () => {
		if (!auth.status?.authenticated) {
			goto('/login', { replaceState: true });
			return;
		}
		await loadUsers();
	});

	async function loadUsers() {
		try {
			const data = await call('GET /api/auth/users');
			users = data.users;
		} catch (err: unknown) {
			usersError = err instanceof ApiError ? err.message : 'Could not load users';
		}
	}

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		error = '';

		if (password !== confirmPassword) {
			error = 'Passwords do not match';
			return;
		}

		busy = true;
		try {
			await api('POST', '/api/auth/register', { username, password });
			username = '';
			password = '';
			confirmPassword = '';
			await loadUsers();
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
		<h1 class="text-2xl font-semibold">Moduskript</h1>
	</div>

	<section class="flex flex-col gap-2">
		<h2 class="flex items-center gap-2 text-sm font-semibold">
			<Users size={16} /> Existing accounts
		</h2>
		{#if usersError}
			<p role="alert" style="color: var(--danger); font-size: 0.875rem;">{usersError}</p>
		{:else if users.length === 0}
			<p style="color: var(--muted); font-size: 0.875rem;">Loading...</p>
		{:else}
			<ul class="flex flex-col gap-1">
				{#each users as u (u.id)}
					<li class="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm"
						style="background: var(--surface); border-color: var(--border)">
						<span class="flex-1 truncate">{u.username}</span>
						{#if u.totp_enabled}
							<ShieldCheck size={14} style="color: var(--success)" title="Two-factor enabled" />
						{/if}
					</li>
				{/each}
			</ul>
		{/if}
	</section>

	<form onsubmit={submit} class="flex flex-col gap-4">
		<p style="color: var(--muted)">Create a new account to log in with.</p>

		<label class="flex flex-col gap-1">
			<span class="text-sm">Username</span>
			<input
				class="rounded-lg border px-3"
				style="background: var(--surface); border-color: var(--border)"
				bind:value={username}
				autocomplete="username"
				autocapitalize="off"
				required
				minlength={3}
				maxlength={64}
			/>
		</label>
		<label class="flex flex-col gap-1">
			<span class="text-sm">Password (at least 10 characters)</span>
			<input
				class="rounded-lg border px-3"
				style="background: var(--surface); border-color: var(--border)"
				type="password"
				bind:value={password}
				autocomplete="new-password"
				minlength={10}
				required
			/>
		</label>
		<label class="flex flex-col gap-1">
			<span class="text-sm">Confirm password</span>
			<input
				class="rounded-lg border px-3"
				style="background: var(--surface); border-color: var(--border)"
				type="password"
				bind:value={confirmPassword}
				autocomplete="new-password"
				required
			/>
		</label>

		{#if error}
			<p role="alert" style="color: var(--danger)">{error}</p>
		{/if}

		<button
			class="rounded-lg px-4 font-medium disabled:opacity-60"
			style="background: var(--accent); color: var(--accent-text)"
			disabled={busy}
		>
			Create account
		</button>
	</form>
</main>