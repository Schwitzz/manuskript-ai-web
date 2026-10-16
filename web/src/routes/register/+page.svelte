<script lang="ts">
	import AppShell from '#lib/components/AppShell.svelte';
	import { api, ApiError, call } from '#lib/api.ts';
	import { auth } from '#lib/stores/auth.svelte.ts';
	import { Users, ShieldCheck, UserPlus, Trash2, KeyRound, Check, X, ArrowLeft } from '@lucide/svelte';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import type { UserRef } from '#lib/api-types.ts';

	let username = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let error = $state('');
	let successMsg = $state('');
	let busy = $state(false);
	let users = $state<UserRef[]>([]);
	let usersError = $state('');

	// Password modification state
	let editingUserId = $state<number | null>(null);
	let newPassword = $state('');
	let confirmNewPassword = $state('');
	let pwError = $state('');
	let pwBusy = $state(false);

	onMount(async () => {
		if (!auth.status?.authenticated) {
			goto('/login', { replaceState: true });
			return;
		}
		await loadUsers();
	});

	async function loadUsers() {
		usersError = '';
		try {
			const data = await call('GET /api/auth/users');
			users = data.users;
		} catch (err: unknown) {
			usersError = err instanceof ApiError ? err.message : 'Could not load users';
		}
	}

	async function submitAddUser(e: SubmitEvent) {
		e.preventDefault();
		error = '';
		successMsg = '';

		if (username.trim().length < 3) {
			error = 'Username must be at least 3 characters';
			return;
		}
		if (password.length < 10) {
			error = 'Password must be at least 10 characters';
			return;
		}
		if (password !== confirmPassword) {
			error = 'Passwords do not match';
			return;
		}

		busy = true;
		try {
			await api('POST', '/api/auth/register', { username: username.trim(), password });
			successMsg = `User "${username.trim()}" created.`;
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

	function startModifyPassword(u: UserRef) {
		editingUserId = u.id;
		newPassword = '';
		confirmNewPassword = '';
		pwError = '';
		successMsg = '';
	}

	function cancelModifyPassword() {
		editingUserId = null;
		newPassword = '';
		confirmNewPassword = '';
		pwError = '';
	}

	async function submitModifyPassword(u: UserRef) {
		pwError = '';
		successMsg = '';
		if (newPassword.length < 10) {
			pwError = 'New password must be at least 10 characters';
			return;
		}
		if (newPassword !== confirmNewPassword) {
			pwError = 'Passwords do not match';
			return;
		}
		pwBusy = true;
		try {
			await api('PUT', `/api/auth/users/${u.id}/password`, { password: newPassword });
			successMsg = `Password updated for "${u.username}".`;
			cancelModifyPassword();
		} catch (err: unknown) {
			pwError = err instanceof ApiError ? err.message : 'Could not update password';
		} finally {
			pwBusy = false;
		}
	}

	async function handleDeleteUser(u: UserRef) {
		if (users.length <= 1) return;
		if (!confirm(`Remove user "${u.username}"? This cannot be undone.`)) return;
		usersError = '';
		successMsg = '';
		try {
			await api('DELETE', `/api/auth/users/${u.id}`);
			successMsg = `Removed user "${u.username}".`;
			await loadUsers();
		} catch (err: unknown) {
			usersError = err instanceof ApiError ? err.message : 'Could not remove user';
		}
	}
</script>

<AppShell title="Users">
	<div class="mx-auto flex max-w-2xl flex-col gap-6">
		<div>
			<button
				type="button"
				class="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium"
				style="border-color: var(--border); background: var(--surface); color: var(--text)"
				onclick={() => goto('/more')}
			>
				<ArrowLeft size={14} /> Back to More
			</button>
		</div>

		{#if successMsg}
			<p
				role="status"
				class="rounded-lg border px-3 py-2 text-sm"
				style="border-color: var(--success); color: var(--success); background: var(--surface)"
			>
				{successMsg}
			</p>
		{/if}

		<!-- Existing Users List with Modify Password & Remove -->
		<section
			class="flex flex-col gap-3 rounded-xl border p-4"
			style="background: var(--surface); border-color: var(--border)"
			aria-label="User Accounts"
		>
			<h2 class="flex items-center gap-2 text-sm font-semibold">
				<Users size={18} style="color: var(--accent)" /> Existing Users
			</h2>
			{#if usersError}
				<p role="alert" style="color: var(--danger); font-size: 0.875rem;">{usersError}</p>
			{:else if users.length === 0}
				<p style="color: var(--muted); font-size: 0.875rem;">Loading...</p>
			{:else}
				<ul class="flex flex-col gap-2">
					{#each users as u (u.id)}
						<li
							class="flex flex-col gap-2 rounded-lg border p-3 text-sm"
							style="background: var(--bg); border-color: var(--border)"
						>
							<div class="flex items-center gap-2">
								<span class="flex-1 truncate font-medium">{u.username}</span>
								{#if u.totp_enabled}
									<span
										class="flex items-center gap-1 rounded px-2 py-0.5 text-xs"
										style="color: var(--success); background: var(--surface)"
										title="Two-factor enabled"
									>
										<ShieldCheck size={13} /> 2FA
									</span>
								{/if}
								<button
									type="button"
									class="flex items-center gap-1 rounded border px-2.5 py-1 text-xs font-medium"
									style="border-color: var(--border); background: var(--surface); color: var(--text)"
									onclick={() =>
										editingUserId === u.id ? cancelModifyPassword() : startModifyPassword(u)}
								>
									<KeyRound size={13} /> Modify Password
								</button>
								<button
									type="button"
									class="flex items-center gap-1 rounded border px-2.5 py-1 text-xs font-medium disabled:opacity-40"
									style="border-color: var(--border); background: var(--surface); color: var(--danger)"
									disabled={users.length <= 1}
									title={users.length <= 1
										? 'Cannot remove the only remaining user'
										: `Remove ${u.username}`}
									onclick={() => handleDeleteUser(u)}
								>
									<Trash2 size={13} /> Remove
								</button>
							</div>

							{#if editingUserId === u.id}
								<div
									class="mt-1 flex flex-col gap-2 rounded-lg border p-3"
									style="border-color: var(--accent); background: var(--surface)"
								>
									<div class="text-xs font-semibold">
										Change password for "{u.username}"
									</div>
									<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
										<label class="flex flex-col gap-1">
											<span class="text-xs" style="color: var(--muted)"
												>New password (10+ chars)</span
											>
											<input
												type="password"
												bind:value={newPassword}
												autocomplete="off"
												class="rounded border px-2.5 py-1.5 text-sm"
												style="background: var(--bg); border-color: var(--border); color: var(--text)"
											/>
										</label>
										<label class="flex flex-col gap-1">
											<span class="text-xs" style="color: var(--muted)">Confirm new password</span>
											<input
												type="password"
												bind:value={confirmNewPassword}
												autocomplete="off"
												class="rounded border px-2.5 py-1.5 text-sm"
												style="background: var(--bg); border-color: var(--border); color: var(--text)"
											/>
										</label>
									</div>
									{#if pwError}
										<p role="alert" class="text-xs" style="color: var(--danger)">{pwError}</p>
									{/if}
									<div class="flex gap-2">
										<button
											type="button"
											disabled={pwBusy}
											onclick={() => submitModifyPassword(u)}
											class="flex items-center gap-1 rounded px-3 py-1.5 text-xs font-medium"
											style="background: var(--accent); color: var(--accent-text)"
										>
											<Check size={13} /> {pwBusy ? 'Saving...' : 'Save Password'}
										</button>
										<button
											type="button"
											onclick={cancelModifyPassword}
											class="flex items-center gap-1 rounded border px-3 py-1.5 text-xs"
											style="border-color: var(--border); color: var(--muted)"
										>
											<X size={13} /> Cancel
										</button>
									</div>
								</div>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</section>

		<!-- Add User Form -->
		<section
			class="flex flex-col gap-4 rounded-xl border p-4"
			style="background: var(--surface); border-color: var(--border)"
			aria-label="Add User"
		>
			<h2 class="flex items-center gap-2 text-sm font-semibold">
				<UserPlus size={18} style="color: var(--accent)" /> Add User
			</h2>
			<form onsubmit={submitAddUser} class="flex flex-col gap-4" novalidate>
				<label class="flex flex-col gap-1">
					<span class="text-sm">Username</span>
					<input
						class="rounded-lg border px-3 py-2 text-sm"
						style="background: var(--bg); border-color: var(--border)"
						bind:value={username}
						autocomplete="off"
						autocapitalize="off"
						spellcheck="false"
						required
					/>
				</label>
				<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
					<label class="flex flex-col gap-1">
						<span class="text-sm">Password (at least 10 characters)</span>
						<input
							class="rounded-lg border px-3 py-2 text-sm"
							style="background: var(--bg); border-color: var(--border)"
							type="password"
							bind:value={password}
							autocomplete="off"
							required
						/>
					</label>
					<label class="flex flex-col gap-1">
						<span class="text-sm">Confirm password</span>
						<input
							class="rounded-lg border px-3 py-2 text-sm"
							style="background: var(--bg); border-color: var(--border)"
							type="password"
							bind:value={confirmPassword}
							autocomplete="off"
							required
						/>
					</label>
				</div>

				{#if error}
					<p role="alert" style="color: var(--danger)">{error}</p>
				{/if}

				<button
					class="rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-60"
					style="background: var(--accent); color: var(--accent-text)"
					disabled={busy}
				>
					{busy ? 'Creating...' : 'Create account'}
				</button>
			</form>
		</section>
	</div>
</AppShell>
