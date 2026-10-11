<script lang="ts">
	import { ai } from '#lib/stores/ai.svelte.ts';
	import { X, Send, Plus, Trash2, BookOpen, RefreshCw } from '@lucide/svelte';
	import ProviderPicker from './ProviderPicker.svelte';
	import ModelPicker from './ModelPicker.svelte';
	import AgentPicker from './AgentPicker.svelte';
	import AIStatusBar from './AIStatusBar.svelte';

	let input = $state('');
	let chatListOpen = $state(false);
	let msgList: HTMLDivElement | null = null;

	// Load chats when panel opens
	$effect(() => {
		if (ai.panelOpen) {
			ai.loadChats();
		}
	});

	// Auto-scroll message list
	$effect(() => {
		const el = msgList as unknown as HTMLElement;
		if (el && ai.messages.length > 0) {
			el.scrollTop = el.scrollHeight;
		}
	});

	async function send() {
		const msg = input.trim();
		if (!msg || ai.streaming.isStreaming) return;
		input = '';
		await ai.send(msg);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			send();
		}
	}

	function formatContent(content: string): string {
		return content
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/\n/g, '<br>');
	}
</script>

<div class="flex h-full w-full flex-col" style="border-color: var(--border)">
	<!-- Header -->
	<div class="flex items-center gap-1 border-b px-2 py-1.5" style="border-color: var(--border)">
		<span class="flex-1 text-sm font-medium">AI Chat</span>
		<button class="rounded p-1" onclick={() => { ai.panelOpen = false; ai.newChat(); }} title="New chat">
			<Plus size={16} style="color: var(--muted)" />
		</button>
		<button class="rounded p-1" onclick={() => { chatListOpen = !chatListOpen; ai.loadChats(); }} title="Chat history">
			<BookOpen size={16} style="color: var(--muted)" />
		</button>
		<button class="rounded p-1" onclick={() => { ai.panelOpen = false; }} title="Close">
			<X size={16} style="color: var(--muted)" />
		</button>
	</div>

	<!-- Provider toolbar -->
	<div class="flex flex-wrap items-center gap-1 border-b px-2 py-1" style="border-color: var(--border)">
		<ProviderPicker />
		<ModelPicker />
		<AgentPicker />
		<button
			class="rounded p-1"
			onclick={() => ai.reloadModels()}
			title="Reload models"
		>
			<RefreshCw size={12} style="color: var(--muted)" />
		</button>
	</div>

	<!-- Chat history sidebar -->
	{#if chatListOpen}
		<div class="absolute right-0 top-12 z-20 h-[calc(100%-3rem)] w-56 border-r overflow-y-auto"
			style="border-color: var(--border); background: var(--surface)">
			<div class="flex items-center justify-between px-2 py-1">
				<span class="text-xs font-medium">Chats</span>
				<button class="rounded p-1" onclick={() => chatListOpen = false}><X size={12} style="color: var(--muted)" /></button>
			</div>
			{#each ai.chats as chat (chat.id)}
				<div class="flex items-center gap-1 px-2 py-1"
					class:active-chat={ai.chatId === chat.id}>
					<button
						class="flex-1 truncate rounded px-1 text-xs"
						onclick={() => { ai.loadChat(chat.id); chatListOpen = false; }}
						title={chat.title}
					>
						{chat.title || 'Untitled'}
					</button>
					<button
						class="rounded p-0.5"
						onclick={() => { ai.deleteChat(chat.id); }}
						title="Delete"
					>
						<Trash2 size={12} style="color: var(--muted)" />
					</button>
				</div>
			{/each}
		</div>
	{/if}

	<!-- Messages -->
	<div
		class="flex-1 overflow-y-auto px-3 py-2"
		class:list={[ai.streaming.isStreaming ? 'pb-8' : 'pb-2']}
		onscrollend={() => {}}
	>
		{#if ai.messages.length === 0}
			<div class="flex h-full items-center justify-center text-sm" style="color: var(--muted)">
				<div class="text-center">
					<p>No messages yet</p>
					<p class="text-xs mt-1">Send a message to start a conversation</p>
				</div>
			</div>
		{:else}
			{#each ai.messages as msg (msg.role + msg.content.slice(0, 20))}
				<div class="mb-2">
					<div class="mb-0.5 text-xs font-medium" style="color: var(--muted)">
						{#if msg.role === 'user'}
							You
						{:else if msg.role === 'assistant'}
							{msg.agent ?? 'AI'}
						{:else}
							System
						{/if}
					</div>
					<div
						class="rounded border px-3 py-2 text-sm"
						style="border-color: var(--border); background: var(--surface)"
					>{@html formatContent(msg.content) || (msg.role === 'assistant' ? 'Thinking...' : '')}
					</div>
				</div>
			{/each}
			{#if ai.streaming.isStreaming}
				<div class="mb-2">
					<div class="mb-0.5 text-xs font-medium" style="color: var(--muted)">{ai.agent}</div>
					<div
						class="rounded border px-3 py-2 text-sm"
						style="border-color: var(--border); background: var(--surface)"
					>{@html formatContent(ai.streaming.currentText) || 'Thinking...'}
					</div>
				</div>
			{/if}
			{#if ai.streaming.error}
				<div class="mb-2 rounded border px-3 py-2 text-sm" style="border-color: red; color: red">
					{ai.streaming.error}
				</div>
			{/if}
		{/if}
	</div>

	<!-- Status bar (streaming indicators) -->
	<AIStatusBar />

	<!-- Input area -->
	<div class="border-t p-2" style="border-color: var(--border)">
		<div class="flex items-end gap-1">
			<textarea
				bind:value={input}
				onkeydown={handleKeydown}
				placeholder="Message {ai.agent}..."
				class="min-h-[2.5rem] max-h-32 w-full resize-none rounded border p-2 text-sm"
				style="border-color: var(--border); background: var(--surface)"
				rows={1}
			/>
			<button
				class="rounded p-2"
				class:disabled={ai.streaming.isStreaming || !input.trim()}
				onclick={send}
				title="Send (Enter)"
			>
				<Send size={18} style="color: {ai.streaming.isStreaming || !input.trim() ? 'var(--muted)' : 'var(--accent)'}" />
			</button>
		</div>
	</div>
</div>
