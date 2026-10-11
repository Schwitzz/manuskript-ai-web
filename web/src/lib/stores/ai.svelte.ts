import { api, csrfToken } from '#lib/api.ts';
import { project } from '#lib/stores/project.svelte.ts';
import type { ChatListEntry } from '#lib/api-types.ts';

const PROVIDERS = ['Local / Llama.cpp', 'OpenAI', 'Anthropic', 'Google Gemini'];
const THINKING_LEVELS = ['Off', 'low', 'med', 'high', 'xhigh'];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ChatMessage {
	role: 'user' | 'assistant' | 'system';
	content: string;
	agent?: string;
}

export interface StreamingState {
	isStreaming: boolean;
	currentText: string;
	thinkingText: string;
	inTokens: number | null;
	outTokens: number | null;
	startTime: number | null;
	error: string | null;
}

export interface ProviderSetting {
	provider: string;
	api_key: string; // write-only: blank means "keep the saved key"
	/** Read-only: true when the server has a key saved for this provider. */
	has_key?: boolean;
	model: string;
	endpoint: string;
	context_size: number;
	temperature: number;
	thinking: string;
}

export interface AgentPrompt {
	name: string;
	prompt: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEFAULT_PROVIDER = 'OpenAI';

// ---------------------------------------------------------------------------
// AI Store
// ---------------------------------------------------------------------------

class AICore {
	// Provider / model
	provider = $state(DEFAULT_PROVIDER);
	model = $state('');
	agent = $state('Co-author');
	temperature = $state(0.7);
	thinking = $state('Off');
	agents = $state<AgentPrompt[]>([]);
	providerModels = $state<Record<string, string[]>>({});
	availableProviders = $state(PROVIDERS);

	// Chat state
	messages = $state<ChatMessage[]>([]);
	/** Follows the project picked in More; chats are filed under it. */
	get project(): string { return project.name ?? ''; }
	/** The scene open in the editor; sent so the model sees its text, summary and POV. */
	sceneId = $state<number | null>(null);
	chatId = $state<string | null>(null);
	chats = $state<ChatListEntry[]>([]);
	contextSources = $state({
		selection: true, scene: true, summary: true, pov: true, book: true,
	});
	contextMaxTokens = $state(2000);
	panelOpen = $state(false);

	// Streaming state
	streaming = $state<StreamingState>({
		isStreaming: false,
		currentText: '',
		thinkingText: '',
		inTokens: null,
		outTokens: null,
		startTime: null,
		error: null,
	});

	// Abort controller for SSE cancellation
	private abortCtrl: AbortController | null = null;
	private _initialized = false;

	get initialized() { return this._initialized; }

	async init() {
		if (this._initialized) return;
		this._initialized = true;
		await this.loadAgents();
		await this.loadProviders();
		if (this.providerModels[this.provider]) {
			this.model = this.providerModels[this.provider][0] ?? '';
		}
	}

	private async loadAgents() {
		try {
			const data = await api<{ agents: AgentPrompt[] }>('GET', '/api/ai/agents');
			this.agents = data.agents;
			if (!this.agents.find((a) => a.name === this.agent)) {
				this.agent = this.agents[0]?.name ?? 'Co-author';
			}
		} catch { /* non-critical */ }
	}

	async loadProviders() {
		for (const prov of this.availableProviders) {
			if (!this.providerModels[prov]) {
				try {
					const data = await api<{ models: string[] }>(
						'GET', `/api/ai/models?provider=${encodeURIComponent(prov)}`
					);
					this.providerModels = { ...this.providerModels, [prov]: data.models };
				} catch {
					this.providerModels = { ...this.providerModels, [prov]: [] };
				}
			}
		}
	}

	async reloadModels() {
		try {
			const data = await api<{ models: string[] }>(
				'GET', `/api/ai/models?provider=${encodeURIComponent(this.provider)}`
			);
			this.providerModels = { ...this.providerModels, [this.provider]: data.models };
			this.model = data.models[0] ?? '';
		} catch {
			this.providerModels = { ...this.providerModels, [this.provider]: [] };
		}
	}

	async loadChats() {
		try {
			const data = await api<{ chats: ChatListEntry[] }>('GET', '/api/ai/chats');
			this.chats = data.chats;
		} catch { /* non-critical */ }
	}

	newChat() {
		this.messages = [];
		this.chatId = null;
		this.streaming = {
			isStreaming: false, currentText: '', thinkingText: '',
			inTokens: null, outTokens: null, startTime: null, error: null,
		};
	}


	private errorToast(msg: string) {
		this.streaming = { ...this.streaming, error: msg, isStreaming: false };
	}

	get systemPrompt(): string {
		return this.agents.find((a) => a.name === this.agent)?.prompt ?? '';
	}

	// -----------------------------------------------------------------------
	// Streaming
	// -----------------------------------------------------------------------

	async send(message: string) {
		if (this.streaming.isStreaming || !message.trim()) return;

		const userMsg: ChatMessage = { role: 'user', content: message };
		const conversation = [...this.messages, userMsg];

		this.streaming = {
			isStreaming: true,
			currentText: '',
			thinkingText: '',
			inTokens: null,
			outTokens: null,
			startTime: Date.now(),
			error: null,
		};
		this.abortCtrl = new AbortController();
		this.messages = [...this.messages, userMsg];

		// A reply is only saved into a chat that exists, so make one for the first message.
		if (!this.chatId) {
			try {
				const made = await api<{ chat_id: string }>('POST', '/api/ai/chats/new', {
					project: this.project, agent: this.agent, messages: [userMsg]
				});
				this.chatId = made.chat_id;
			} catch { /* chatting still works, it just will not be saved */ }
		}

		try {
			const res = await fetch('/api/ai/chat', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', 'x-csrf-token': csrfToken() },
				body: JSON.stringify({
					project: this.project,
					scene_id: this.sceneId,
					chat_id: this.chatId,
					messages: conversation.map((m) => ({ role: m.role, content: m.content })),
					provider: this.provider,
					model: this.model,
					agent: this.agent,
					temperature: this.temperature,
					thinking: this.thinking,
					context_sources: this.contextSources,
					context_max_tokens: this.contextMaxTokens,
				}),
				signal: this.abortCtrl.signal,
			});

			if (!res.ok) {
				let msg = 'Request failed';
				try { const j = await res.json(); msg = typeof j.detail === 'string' ? j.detail : msg; } catch { /* */ }
				throw new Error(msg);
			}

			const reader = res.body?.getReader();
			if (!reader) throw new Error('No response body');

			const decoder = new TextDecoder();
			let buffer = '';
			let accumulatedText = '';
			let thinkingText = '';
			let inTokens: number | null = null;
			let outTokens: number | null = null;
			let sawDone = false;

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				buffer = lines.pop() ?? '';
				for (const line of lines) {
					const trimmed = line.trim();
					if (!trimmed.startsWith('data:')) continue;
					const jsonStr = trimmed.slice(5).trim();
					if (!jsonStr || jsonStr === '[DONE]') continue;
					try {
						const evt = JSON.parse(jsonStr) as Record<string, unknown>;
						if (evt.error) throw new Error(typeof evt.error === 'string' ? evt.error : JSON.stringify(evt.error));
						inTokens = (evt.inTokens as number) ?? inTokens;
						outTokens = (evt.outTokens as number) ?? outTokens;
						// Both `thinking` and `text` arrive as the next piece, except in the final `done` event.
						if (evt.done) {
							if (typeof evt.thinking === 'string') thinkingText = evt.thinking;
							sawDone = true;
							accumulatedText = (evt.text as string) ?? accumulatedText; // the server's final full text
						} else {
							if (typeof evt.thinking === 'string') thinkingText += evt.thinking;
							if (typeof evt.text === 'string') accumulatedText += evt.text;
						}
						this.streaming = { ...this.streaming, thinkingText, currentText: accumulatedText, inTokens, outTokens };
					} catch (e) {
						if (e instanceof Error && e.name === 'AbortError') throw e;
						throw e;
					}
				}
			}

			if (!sawDone) throw new Error('The reply was cut off before it finished.');
			this.messages = [...this.messages, { role: 'assistant', content: accumulatedText, agent: this.agent }];
			this.streaming = { isStreaming: false, currentText: accumulatedText, thinkingText, inTokens, outTokens, startTime: null, error: null };
		} catch (e) {
			if (e instanceof Error && e.name === 'AbortError') {
				this.messages = this.messages.slice(0, -1);
			} else {
				this.errorToast(e instanceof Error ? e.message : 'Streaming failed');
				this.messages = this.messages.slice(0, -1);
			}
		} finally {
			this.abortCtrl = null;
		}
	}

	// -----------------------------------------------------------------------
	// Provider settings
	// -----------------------------------------------------------------------

	providerSettings = $state<ProviderSetting[]>([]);
	agentPrompts = $state<AgentPrompt[]>([]);

	async loadProviderSettings() {
		try {
			const data = await api<{ settings: ProviderSetting[] }>('GET', '/api/ai/providers');
			this.providerSettings = data.settings ?? [];
		} catch { /* non-critical */ }
	}

	async saveProviderSettings(settings: ProviderSetting[]) {
		await api<{ ok: boolean }>('POST', '/api/ai/providers', { settings });
		this.providerSettings = settings;
	}

	async loadAgentPrompts() {
		try {
			const data = await api<{ agents: AgentPrompt[] }>('GET', '/api/ai/agents');
			this.agentPrompts = data.agents ?? [];
		} catch { /* non-critical */ }
	}

	async saveAgentPrompt(name: string, prompt: string) {
		await api<{ agents: AgentPrompt[] }>('PUT', '/api/ai/agents', { name, prompt });
		await this.loadAgentPrompts();
	}

	// -----------------------------------------------------------------------
	// Chat list / history
	// -----------------------------------------------------------------------

	async loadChatList() {
		try {
			const data = await api<{ chats: ChatListEntry[] }>('GET', '/api/ai/chats');
			this.chats = data.chats ?? [];
		} catch { /* non-critical */ }
	}

	async loadChat(chatId: string) {
		try {
			const data = await api<unknown>('GET', `/api/ai/chats/${encodeURIComponent(chatId)}`);
			const typed = data as { messages: ChatMessage[]; title: string; id: string };
			this.chatId = chatId;
			this.messages = typed.messages ?? [];
			this.panelOpen = true;
			await this.loadChatList();
		} catch (e) {
			this.errorToast(e instanceof Error ? e.message : 'Failed to load chat');
		}
	}

	async createChat() {
		try {
			const data = await api<{ ok: boolean; chat_id: string }>('POST', '/api/ai/chats/new', {
				project: this.project,
				messages: [],
			});
			this.chatId = data.chat_id;
			this.messages = [];
			this.panelOpen = true;
			await this.loadChatList();
		} catch (e) {
			this.errorToast(e instanceof Error ? e.message : 'Failed to create chat');
		}
	}

	async deleteChat(chatId: string) {
		await api('DELETE', `/api/ai/chats/${encodeURIComponent(chatId)}`);
		if (this.chatId === chatId) {
			this.chatId = null;
			this.messages = [];
			this.panelOpen = false;
		}
		await this.loadChatList();
	}

	async renameChat(chatId: string, title: string) {
		await api<{ ok: boolean }>('PUT', `/api/ai/chats/${encodeURIComponent(chatId)}`, { title });
		await this.loadChatList();
	}

	cancel() {
		if (this.abortCtrl) this.abortCtrl.abort();
	}

	get tokensPerSecond(): number | null {
		if (!this.streaming.startTime || !this.streaming.outTokens) return null;
		const elapsed = (Date.now() - this.streaming.startTime) / 1000;
		return elapsed > 0 ? Math.round(this.streaming.outTokens / elapsed) : null;
	}

	get tokensPerSecondFormatted(): string | null {
		const tps = this.tokensPerSecond;
		return tps !== null ? `${tps}/s` : null;
	}

	get elapsedSeconds(): number {
		if (!this.streaming.startTime) return 0;
		return Math.round((Date.now() - this.streaming.startTime) / 1000);
	}
}

export const ai = new AICore();