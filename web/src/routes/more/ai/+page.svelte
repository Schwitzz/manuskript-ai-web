<script lang="ts">
import AppShell from '#lib/components/AppShell.svelte';
import { ai, type ProviderSetting, SUGGESTED_MODELS } from '#lib/stores/ai.svelte.ts';
import { Settings, Save, RotateCcw, Trash2, Plus, MessageSquare, Pencil, X, RefreshCw, Check } from '@lucide/svelte';
import { onMount } from 'svelte';

let saving = $state(false);
let fetchingProvider = $state<string | null>(null);
let savingAgent = $state<string | null>(null);
let editingAgent = $state<string | null>(null);
let editingPrompt = $state('');
let showChatHistory = $state(false);
let renamingChat = $state<string | null>(null);
let renameValue = $state('');
let toastMsg = $state<string | null>(null);

const TOAST_DURATION = 3000;

onMount(async () => {
await Promise.all([
ai.loadProviderSettings(),
ai.loadAgentPrompts(),
ai.loadChatList(),
ai.loadProviders()
]);
});

async function handleFetchModels(setting: ProviderSetting) {
	fetchingProvider = setting.provider;
	try {
		await ai.saveProviderSettings(ai.providerSettings);
		const models = await ai.fetchModelsForProvider(setting.provider);
		if (models.length > 0 && !setting.model) {
			setting.model = models[0];
			await ai.saveProviderSettings(ai.providerSettings);
		}
		showToast(`Loaded ${models.length} models for ${setting.provider}`);
	} catch (e) {
		showToast(e instanceof Error ? e.message : `Could not fetch models for ${setting.provider}`);
	} finally {
		fetchingProvider = null;
	}
}

function selectActiveProvider(setting: ProviderSetting) {
	ai.provider = setting.provider;
	if (setting.model) {
		ai.model = setting.model;
	} else {
		const fallback = ai.modelsForProvider(setting.provider)[0] ?? '';
		setting.model = fallback;
		ai.model = fallback;
	}
	void handleSaveSettings();
}

function showToast(msg: string) {
toastMsg = msg;
setTimeout(() => { toastMsg = null; }, TOAST_DURATION);
}

async function handleSaveSettings() {
saving = true;
try {
await ai.saveProviderSettings(ai.providerSettings);
showToast('Provider settings saved');
} catch {
showToast('Failed to save settings');
} finally {
saving = false;
}
}

function handleResetSettings() {
ai.loadProviderSettings();
showToast('Settings reset to last saved');
}

function startEditAgent(agent: { name: string; prompt: string }) {
editingAgent = agent.name;
editingPrompt = agent.prompt;
}

function cancelEditAgent() {
editingAgent = null;
editingPrompt = '';
}

async function saveAgentPrompt() {
if (!editingAgent) return;
savingAgent = editingAgent;
try {
await ai.saveAgentPrompt(editingAgent, editingPrompt);
showToast('Agent prompt saved');
editingAgent = null;
editingPrompt = '';
} catch {
showToast('Failed to save agent prompt');
} finally {
savingAgent = null;
}
}

async function handleDeleteChat(chatId: string, e: Event) {
e.stopPropagation();
if (!confirm('Delete this chat? This cannot be undone.')) return;
await ai.deleteChat(chatId);
showToast('Chat deleted');
}

async function handleRenameChat(chatId: string, e: Event) {
e.stopPropagation();
renameValue = '';
renamingChat = chatId;
}

async function confirmRename() {
if (!renamingChat || !renameValue.trim()) {
cancelRename();
return;
}
const chatId = renamingChat;
try {
await ai.renameChat(chatId, renameValue.trim());
showToast('Chat renamed');
} catch {
showToast('Failed to rename chat');
}
renamingChat = null;
renameValue = '';
}

function cancelRename() {
renamingChat = null;
renameValue = '';
}

$effect(() => {
if (ai.providerSettings.length === 0) {
ai.providerSettings = ai.availableProviders.map((p) => ({
provider: p,
api_key: '',
model: '',
endpoint: '',
context_size: 4096,
temperature: ai.temperature,
thinking: ai.thinking,
}));
}
});
</script>

<AppShell title="AI Settings">
<div class="mx-auto flex max-w-2xl flex-col gap-6">
<!-- Toast notification -->
{#if toastMsg}
<div class="fixed right-4 top-4 z-50 rounded-lg border border-green-500/30 bg-green-500/10 px-4 py-2 text-sm text-green-400 backdrop-blur-sm">
{toastMsg}
</div>
{/if}

<!-- Provider Settings -->
<section class="rounded-lg border p-4" style="border-color: var(--border); background: var(--surface)">
<div class="mb-4 flex items-center justify-between">
<div class="flex items-center gap-2">
<Settings size={20} />
<h2 class="text-lg font-semibold">Provider Settings</h2>
</div>
<div class="flex gap-2">
<button
class="flex items-center gap-1 rounded px-2 py-1 text-sm"
style="color: var(--muted); background: transparent"
onclick={handleResetSettings}
disabled={saving}
>
<RotateCcw size={14} /> Reset
</button>
<button
class="flex items-center gap-1 rounded px-3 py-1 text-sm font-medium"
class:opacity-50={saving}
style="background: var(--primary); color: var(--primary-fg)"
onclick={handleSaveSettings}
disabled={saving}
>
{#if saving}
<Save size={14} class="animate-spin" /> Saving...
{:else}
<Save size={14} /> Save
{/if}
</button>
</div>
</div>

<div class="flex flex-col gap-4">
{#each ai.providerSettings as setting, idx (setting.provider)}
{@const modelChoices = Array.from(new Set([...(ai.providerModels[setting.provider] ?? []), ...(SUGGESTED_MODELS[setting.provider] ?? []), ...(setting.model ? [setting.model] : [])]))}
<div class="rounded-lg border p-3" style="background: var(--surface-raised); border-color: {ai.provider === setting.provider ? 'var(--accent)' : 'var(--border)'}">
<div class="mb-3 flex flex-wrap items-center justify-between gap-2">
<div class="flex items-center gap-2">
	<h3 class="font-medium">{setting.provider}</h3>
	{#if setting.has_key}
		<span class="rounded bg-green-500/15 px-2 py-0.5 text-[11px] font-medium text-green-400">API key saved</span>
	{/if}
</div>
<div class="flex items-center gap-2">
	<span class="rounded border px-2 py-0.5 text-xs font-medium" style="border-color: var(--border); color: {setting.model ? 'var(--accent)' : 'var(--muted)'}">
		{setting.model || 'Select a model below'}
	</span>
	<button
		type="button"
		class="flex items-center gap-1 rounded px-2.5 py-1 text-xs font-medium"
		style="background: {ai.provider === setting.provider ? 'var(--accent)' : 'var(--surface)'}; color: {ai.provider === setting.provider ? 'var(--accent-text)' : 'var(--text)'}; border: 1px solid var(--border)"
		onclick={() => selectActiveProvider(setting)}
	>
		{#if ai.provider === setting.provider}<Check size={12} /> Active{:else}Set Active{/if}
	</button>
</div>
</div>

<div class="flex flex-col gap-3">
<div>
<label for={`model-select-${idx}`} class="mb-1 block text-xs font-medium" style="color: var(--muted)">
Default Model
</label>
<div class="flex flex-wrap gap-2">
	<select
		id={`model-select-${idx}`}
		aria-label={`Default model for ${setting.provider}`}
		bind:value={setting.model}
		onchange={() => { if (ai.provider === setting.provider) ai.model = setting.model; }}
		class="min-w-[180px] flex-1 rounded border px-3 py-2 text-sm"
		style="border-color: var(--border); background: var(--surface); color: var(--fg)"
	>
		<option value="">-- Choose a model --</option>
		{#each modelChoices as m (m)}
			<option value={m}>{m}</option>
		{/each}
	</select>
	<input
		type="text"
		aria-label={`Custom model ID for ${setting.provider}`}
		bind:value={setting.model}
		oninput={() => { if (ai.provider === setting.provider) ai.model = setting.model; }}
		class="min-w-[160px] flex-1 rounded border px-3 py-2 text-sm"
		style="border-color: var(--border); background: var(--surface); color: var(--fg)"
		placeholder="Or type custom model ID..."
	/>
	<button
		type="button"
		class="flex items-center gap-1.5 rounded border px-3 py-2 text-xs font-medium"
		style="border-color: var(--border); background: var(--surface); color: var(--text)"
		disabled={fetchingProvider === setting.provider}
		onclick={() => handleFetchModels(setting)}
		title="Save key/endpoint and fetch models from provider"
	>
		<RefreshCw size={13} class={fetchingProvider === setting.provider ? 'animate-spin' : ''} />
		{fetchingProvider === setting.provider ? 'Fetching...' : 'Fetch Models'}
	</button>
</div>
</div>

<div>
<label for={`api_key_${idx}`} class="mb-1 block text-xs font-medium" style="color: var(--muted)">
API Key
</label>
<input
id={`api_key_${idx}`}
type="password"
bind:value={setting.api_key}
class="w-full rounded border px-3 py-2 text-sm"
style="border-color: var(--border); background: var(--surface); color: var(--fg)"
placeholder={setting.has_key ? '•••••••• (saved — enter new key to replace)' : 'Enter your API key...'}
/>
</div>

<div class="grid grid-cols-2 gap-3">
<div>
<label for="endpoint" class="mb-1 block text-xs font-medium" style="color: var(--muted)">
Custom Endpoint
</label>
<input
id="endpoint"
type="url"
bind:value={setting.endpoint}
class="w-full rounded px-3 py-2 text-sm"
style="border-color: var(--border); background: var(--surface); color: var(--fg)"
placeholder="https://..."
/>
</div>
<div>
<label for="context-size" class="mb-1 block text-xs font-medium" style="color: var(--muted)">
Context Size
</label>
<input
id="context-size"
type="number"
bind:value={setting.context_size}
class="w-full rounded px-3 py-2 text-sm"
style="border-color: var(--border); background: var(--surface); color: var(--fg)"
min={512}
max={131072}
step={512}
/>
</div>
</div>

<div class="grid grid-cols-2 gap-3">
<div>
<label for="temperature" class="mb-1 block text-xs font-medium" style="color: var(--muted)">
Temperature
</label>
<input
id="temperature"
type="range"
bind:value={setting.temperature}
class="w-full"
min={0}
max={2}
step={0.1}
/>
<span class="text-xs" style="color: var(--muted)">{setting.temperature}</span>
</div>
<div>
<label for="thinking" class="mb-1 block text-xs font-medium" style="color: var(--muted)">
Thinking Level
</label>
<select
id="thinking"
bind:value={setting.thinking}
class="w-full rounded px-3 py-2 text-sm"
style="border-color: var(--border); background: var(--surface); color: var(--fg)">
<option value="Off">Off</option>
<option value="low">Low</option>
<option value="med">Medium</option>
<option value="high">High</option>
<option value="xhigh">Extra High</option>
</select>
</div>
</div>
</div>
</div>
{/each}
</div>
</section>

<!-- Agent Prompts -->
<section class="rounded-lg border p-4" style="border-color: var(--border); background: var(--surface)">
<div class="mb-4 flex items-center justify-between">
<div class="flex items-center gap-2">
<MessageSquare size={20} />
<h2 class="text-lg font-semibold">Agent Prompts</h2>
</div>
</div>

<div class="flex flex-col gap-3">
{#each ai.agentPrompts as agent}
{#if editingAgent === agent.name}
<!-- Editing mode -->
<div class="rounded-lg p-3" style="background: var(--surface-raised)">
<div class="mb-2 flex items-center justify-between">
<span class="font-medium">{agent.name}</span>
<div class="flex gap-1">
<button
class="rounded px-2 py-1 text-xs"
style="color: var(--success); background: transparent"
onclick={saveAgentPrompt}
disabled={savingAgent === agent.name}
>
<Save size={12} />
</button>
<button
class="rounded px-2 py-1 text-xs"
style="color: var(--danger); background: transparent"
onclick={cancelEditAgent}
>
<X size={12} />
</button>
</div>
</div>
<textarea
bind:value={editingPrompt}
class="w-full rounded px-3 py-2 text-sm"
rows={6}
style="border-color: var(--border); background: var(--surface); color: var(--fg); resize: vertical">
</textarea>
</div>
{:else}
<!-- View mode -->
<div class="flex items-start justify-between rounded-lg p-3" style="background: var(--surface-raised)">
<div class="flex-1">
<div class="mb-1 flex items-center gap-2">
<span class="font-medium">{agent.name}</span>
</div>
<pre class="max-h-24 overflow-auto text-xs whitespace-pre-wrap" style="color: var(--muted)">
{agent.prompt}
</pre>
</div>
<button
class="ml-3 rounded p-1"
style="color: var(--muted); background: transparent"
onclick={() => startEditAgent(agent)}
disabled={savingAgent !== null}
>
<Pencil size={14} />
</button>
</div>
{/if}
{/each}
</div>
</section>

<!-- Context Sources -->
<section class="rounded-lg border p-4" style="border-color: var(--border); background: var(--surface)">
<div class="mb-4 flex items-center justify-between">
<div class="flex items-center gap-2">
<Settings size={20} />
<h2 class="text-lg font-semibold">Context Sources</h2>
</div>
</div>

<div class="flex flex-col gap-3">
{#each Object.entries(ai.contextSources) as [key, value]}
<div class="flex items-center justify-between">
<label class="text-sm" style="color: var(--fg)" for={`ctx-source-${key}`}>
{key.charAt(0).toUpperCase() + key.slice(1)}
</label>
<button
aria-label={`Toggle ${key.charAt(0).toUpperCase() + key.slice(1)}`}
id={`ctx-source-${key}`}
role="switch"
aria-checked={value}
class="relative h-6 w-11 rounded-full transition-colors"
class:bg-green-500={value}
class:bg-gray-600={!value}
onclick={() => ai.contextSources = { ...ai.contextSources, [key]: !value }}
>
<span
class="absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform"
class:translate-x-5={value}
class:translate-x-0.5={!value}
></span>
</button>
</div>
{/each}

<div>
<label for="ctx-max-tokens" class="mb-1 block text-sm font-medium" style="color: var(--muted)">
Max Context Tokens: {ai.contextMaxTokens}
</label>
<input
id="ctx-max-tokens"
type="range"
bind:value={ai.contextMaxTokens}
class="w-full"
min={256}
max={8192}
step={256}
/>
</div>
</div>
</section>

<!-- Chat History -->
<section class="rounded-lg border p-4" style="border-color: var(--border); background: var(--surface)">
<div class="mb-4 flex items-center justify-between">
<div class="flex items-center gap-2">
<MessageSquare size={20} />
<h2 class="text-lg font-semibold">Chat History</h2>
</div>
<button
class="flex items-center gap-1 rounded px-3 py-1 text-sm font-medium"
style="background: var(--primary); color: var(--primary-fg)"
onclick={() => ai.createChat()}
>
<Plus size={14} /> New Chat
</button>
</div>

{#if ai.chats.length === 0}
<p class="py-8 text-center text-sm" style="color: var(--muted)">
No chats yet. Create a new chat to get started.
</p>
{:else}
<div class="flex flex-col gap-2">
{#each ai.chats as chat}
{#if renamingChat === chat.id}
<div class="group flex items-center gap-2 rounded-lg p-3 transition-colors bg-primary/10"
onclick={(e) => e.stopPropagation()}
role="button"
tabindex="0"
onkeydown={(e) => { if (e.key === 'Enter') confirmRename(); }}>
<MessageSquare size={16} style="color: var(--muted)" />
<div class="flex-1 flex gap-2">
<input
	type="text"
	bind:value={renameValue}
	class="flex-1 rounded px-2 py-1 text-sm bg-transparent border"
	style="border-color: var(--border); color: var(--fg)"
	onkeyup={(e) => {
		if (e.key === 'Enter') confirmRename();
		if (e.key === 'Escape') cancelRename();
	}}
/>
<button class="rounded p-1" style="color: var(--success); background: transparent"
	onclick={confirmRename}><Pencil size={14} /></button>
<button class="rounded p-1" style="color: var(--danger); background: transparent"
	onclick={cancelRename}><X size={14} /></button>
</div>
</div>
{:else}
<div class="group flex items-center gap-2 rounded-lg p-3 transition-colors {ai.chatId === chat.id ? "bg-primary/10" : ""}" style="cursor: pointer" onclick={() => ai.loadChat(chat.id)}
role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter') ai.loadChat(chat.id); }}>
<MessageSquare size={16} style="color: var(--muted)" />
<div class="flex-1">
<div class="text-sm font-medium">{chat.title}</div>
<div class="text-xs" style="color: var(--muted)">
{new Date(chat.updated * 1000).toLocaleDateString()}
</div>
</div>
<div class="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
<button
class="rounded p-1"
style="color: var(--muted); background: transparent"
onclick={(e) => handleRenameChat(chat.id, e)}
>
<Pencil size={14} />
</button>
<button
class="rounded p-1"
style="color: var(--danger); background: transparent"
onclick={(e) => handleDeleteChat(chat.id, e)}
>
<Trash2 size={14} />
</button>
</div>
</div>
{/if}
{/each}
</div>
{/if}
</section>
</div>
</AppShell>

<style>
pre {
font-family: var(--font-mono);
}
</style>
