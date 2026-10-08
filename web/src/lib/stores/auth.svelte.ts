import { api, type AuthStatus } from '#lib/api.ts';

class AuthStore {
	status = $state<AuthStatus | null>(null);

	async refresh() {
		this.status = await api<AuthStatus>('GET', '/api/auth/status');
		return this.status;
	}

	async logout() {
		await api('POST', '/api/auth/logout');
		await this.refresh();
	}
}

export const auth = new AuthStore();
