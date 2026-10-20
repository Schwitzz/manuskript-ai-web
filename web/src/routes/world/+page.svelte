<script lang="ts">
	import AppShell from '#lib/components/AppShell.svelte';
	import NoProject from '#lib/components/NoProject.svelte';
	import ProjectNav from '#lib/components/ProjectNav.svelte';
	import { project } from '#lib/stores/project.svelte.ts';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import {
		ChevronRight, Plus, Trash2, Search, Globe, Sparkles, Check, FolderPlus
	} from '@lucide/svelte';
	import { call } from '#lib/api';
	import { addToast } from '#lib/stores/toast.svelte.ts';
	import { onMount } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';

	const PROJECT = $derived(project.name ?? '');

	interface WorldItem {
		id: number;
		name: string;
		description: string;
		passion: string;
		conflict: string;
		children: WorldItem[];
	}

	// Desktop Manuskript's built-in Fantasy World Building starter hierarchy (`worldModel.py`)
	const WORLD_PRESETS: { label: string; children: string[] }[] = [
		{
			label: 'Physical',
			children: ['Climate', 'Topography', 'Astronomy', 'Natural resources', 'Wild life', 'Flora', 'History', 'Races', 'Diseases']
		},
		{
			label: 'Cultural',
			children: [
				'Customs', 'Food', 'Languages', 'Education', 'Dresses', 'Science', 'Calendar',
				'Ethics', 'Religion', 'Government', 'Politics', 'Music and arts', 'Architecture',
				'Military', 'Technology', 'Transportation', 'Medicine'
			]
		},
		{
			label: 'Magic / Technology System',
			children: ['Rules', 'Organization', 'Magical objects', 'Magical places', 'Magical races']
		},
		{
			label: 'Important Places & Objects',
			children: ['Capital / Hub', 'Ancient Ruins', 'Key Artifact']
		}
	];

	let items: WorldItem[] = $state([]);
	let loading = $state(true);
	let saving = $state(false);
	let saved = $state(true);
	let error = $state('');
	let filterQuery = $state('');
	let expanded = new SvelteSet<number>();
	let selectedId: number | null = $state(null);
	let activeDetailTab = $state<'description' | 'conflict'>('description');
	let presetsOpen = $state(false);

	let draftName = $state('');
	let draftDescription = $state('');
	let draftPassion = $state('');
	let draftConflict = $state('');

	function toggle(id: number) {
		if (expanded.has(id)) expanded.delete(id);
		else expanded.add(id);
	}

	function expandAll(list: WorldItem[]) {
		for (const it of list) {
			if (it.children.length > 0) {
				expanded.add(it.id);
				expandAll(it.children);
			}
		}
	}

	function flattenItems(
		list: WorldItem[],
		depth = 0,
		parentId: number | null = null
	): (WorldItem & { depth: number; parentId: number | null })[] {
		const result: (WorldItem & { depth: number; parentId: number | null })[] = [];
		const q = filterQuery.trim().toLowerCase();
		for (const item of list) {
			const matchesSelf =
				!q ||
				item.name.toLowerCase().includes(q) ||
				item.description.toLowerCase().includes(q) ||
				item.passion.toLowerCase().includes(q) ||
				item.conflict.toLowerCase().includes(q);
			const childFlat = flattenItems(item.children, depth + 1, item.id);
			if (matchesSelf || childFlat.length > 0) {
				result.push({ ...item, depth, parentId });
				if (q || expanded.has(item.id)) {
					result.push(...childFlat);
				}
			}
		}
		return result;
	}

	function findItemById(list: WorldItem[], id: number): WorldItem | null {
		for (const item of list) {
			if (item.id === id) return item;
			const found = findItemById(item.children, id);
			if (found) return found;
		}
		return null;
	}

	const selectedItem = $derived(selectedId !== null ? findItemById(items, selectedId) : null);

	function selectItem(item: WorldItem) {
		selectedId = item.id;
		draftName = item.name;
		draftDescription = item.description;
		draftPassion = item.passion;
		draftConflict = item.conflict;
		saved = true;
	}

	async function createWorldNode(name: string, parentId: number | null = null): Promise<WorldItem | null> {
		try {
			const res = (await call('POST /api/projects/{name}/world', {
				params: { name: PROJECT },
				body: { name, parent_id: parentId }
			} as any)) as WorldItem;
			res.children = [];
			if (parentId !== null) {
				const parent = findItemById(items, parentId);
				if (parent) {
					parent.children = [...parent.children, res];
					expanded.add(parentId);
				}
			} else {
				items = [...items, res];
			}
			selectItem(res);
			return res;
		} catch (e: any) {
			error = e.message;
			return null;
		}
	}

	async function addNewItem(parentId: number | null = null) {
		await createWorldNode('New item', parentId);
	}

	async function insertPresetCategory(preset: { label: string; children: string[] }) {
		presetsOpen = false;
		const rootNode = await createWorldNode(preset.label, null);
		if (!rootNode) return;
		for (const childName of preset.children) {
			await createWorldNode(childName, rootNode.id);
		}
		selectItem(rootNode);
	}

	async function saveSelected() {
		if (selectedId === null || !draftName.trim()) return;
		saving = true;
		saved = false;
		try {
			const updated = (await call('PATCH /api/projects/{name}/world/{item_id}', {
				params: { name: PROJECT, item_id: selectedId },
				body: {
					name: draftName.trim(),
					description: draftDescription,
					passion: draftPassion,
					conflict: draftConflict
				}
			})) as WorldItem;
			const target = findItemById(items, selectedId);
			if (target) {
				target.name = updated.name;
				target.description = updated.description;
				target.passion = updated.passion;
				target.conflict = updated.conflict;
			}
			saved = true;
		} catch (e: any) {
			error = e.message;
		} finally {
			saving = false;
		}
	}

	function findParentList(list: WorldItem[], id: number): WorldItem[] | null {
		if (list.some((x) => x.id === id)) return list;
		for (const item of list) {
			const found = findParentList(item.children, id);
			if (found) return found;
		}
		return null;
	}

	async function removeItem(item: WorldItem) {
		if (!confirm(`Delete "${item.name}"?`)) return;
		try {
			await call('DELETE /api/projects/{name}/world/{item_id}', {
				params: { name: PROJECT, item_id: item.id }
			});
			const parentList = findParentList(items, item.id) ?? items;
			const parentId =
				parentList === items
					? null
					: (flattenItems(items).find((x) => x.children === parentList)?.id ?? null);
			const idx = parentList.findIndex((x) => x.id === item.id);
			if (idx !== -1) parentList.splice(idx, 1);
			if (selectedId === item.id) {
				selectedId = items[0]?.id ?? null;
				if (items[0]) selectItem(items[0]);
			}
			addToast(`"${item.name}" deleted`, {
				actionLabel: 'Undo',
				onAction: () => {
					void restoreItem(item, parentId);
				}
			});
		} catch (e: any) {
			error = e.message;
		}
	}

	async function restoreItem(original: WorldItem, parentId: number | null) {
		try {
			const s = (await call('POST /api/projects/{name}/world', {
				params: { name: PROJECT },
				body: {
					name: original.name,
					description: original.description || undefined,
					passion: original.passion || undefined,
					conflict: original.conflict || undefined,
					parent_id: parentId
				}
			} as any)) as WorldItem;
			s.children = [];
			const list = parentId === null ? items : findItemById(items, parentId)?.children;
			if (!list) {
				await reloadWorld();
				return;
			}
			list.push(s);
			for (const child of original.children) await restoreItem(child, s.id);
		} catch (e: any) {
			error = e.message;
		}
	}

	async function reloadWorld() {
		const data = await call('GET /api/projects/{name}/world', { params: { name: PROJECT } });
		items = (data.items ?? []) as WorldItem[];
		expandAll(items);
		if (items.length > 0 && selectedId === null) {
			selectItem(items[0]);
		}
	}

	onMount(async () => {
		if (!PROJECT) {
			loading = false;
			return;
		}
		try {
			await reloadWorld();
		} catch (e: any) {
			error = e.message;
		} finally {
			loading = false;
		}
	});
</script>

<AppShell title="World Builder">
	<div class="mx-auto flex max-w-5xl flex-col gap-4">
		<ProjectNav active="world" />
		{#if !PROJECT}
			<NoProject />
		{:else if loading}
			<p style="color: var(--muted)">Loading world...</p>
		{:else if error}
			<p role="alert" style="color: var(--danger)">{error}</p>
		{:else}
			<p class="text-xs" style="color: var(--muted)">
				Build worlds. Create a hierarchy of broad categories down to specific details (<code>world.opml</code>).
			</p>

			<div class="grid grid-cols-1 gap-4 md:grid-cols-12">
				<!-- Left Pane: World Tree + Toolbar (Desktop parity) -->
				<div
					class="flex flex-col gap-3 rounded-lg border p-3 md:col-span-5"
					style="border-color: var(--border); background: var(--surface)"
				>
					<div class="flex items-center gap-1.5">
						<button
							type="button"
							class="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium"
							style="background: var(--accent); color: var(--accent-text)"
							title="Add root world item"
							onclick={() => addNewItem(null)}
						>
							<Plus size={14} /> Add Root
						</button>
						{#if selectedItem}
							<button
								type="button"
								class="flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs font-medium"
								style="border-color: var(--border); color: var(--text)"
								title="Add child under selected item"
								onclick={() => addNewItem(selectedItem.id)}
							>
								<FolderPlus size={14} /> + Child
							</button>
						{/if}
						<div class="relative ml-auto">
							<button
								type="button"
								class="flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs font-medium"
								style="border-color: var(--border); color: var(--text)"
								title="Insert guided world-building prompts"
								onclick={() => (presetsOpen = !presetsOpen)}
							>
								<Sparkles size={14} style="color: var(--accent)" /> Prompts
							</button>
							{#if presetsOpen}
								<div
									class="absolute right-0 top-full z-20 mt-1 w-56 rounded-lg border p-1.5 shadow-xl"
									style="background: var(--surface); border-color: var(--border)"
								>
									<div class="px-2 py-1 text-[10px] font-semibold uppercase" style="color: var(--muted)">
										World Building Guides
									</div>
									{#each WORLD_PRESETS as preset (preset.label)}
										<button
											type="button"
											class="w-full rounded px-2.5 py-1.5 text-left text-xs hover:opacity-80"
											style="color: var(--text)"
											onclick={() => insertPresetCategory(preset)}
										>
											+ {preset.label} ({preset.children.length})
										</button>
									{/each}
								</div>
							{/if}
						</div>
					</div>

					<div class="relative">
						<Search size={14} class="absolute left-2.5 top-2.5" style="color: var(--muted)" />
						<input
							class="w-full rounded-lg border py-1.5 pl-8 pr-3 text-xs"
							style="background: var(--bg); border-color: var(--border); color: var(--text)"
							placeholder="Filter world items..."
							bind:value={filterQuery}
						/>
					</div>

					{#if items.length === 0}
						<EmptyState title="No world items yet">
							<div class="flex flex-wrap justify-center gap-2">
								<button
									class="rounded-lg px-3 py-1.5 text-xs font-medium"
									style="background: var(--accent); color: var(--accent-text)"
									onclick={() => addNewItem(null)}
								>
									Add first item
								</button>
								<button
									class="rounded-lg border px-3 py-1.5 text-xs font-medium"
									style="border-color: var(--border); color: var(--text)"
									onclick={() => insertPresetCategory(WORLD_PRESETS[0])}
								>
									Insert Fantasy Starter Set
								</button>
							</div>
						</EmptyState>
					{:else}
						<div class="flex max-h-[60vh] flex-col gap-1 overflow-y-auto pr-1">
							{#each flattenItems(items) as item (item.id)}
								<div
									class="flex cursor-pointer items-center gap-1.5 rounded-lg border px-2 py-1.5 text-sm"
									style="margin-left: {item.depth * 18}px; border-color: {selectedId === item.id ? 'var(--accent)' : 'var(--border)'}; background: {selectedId === item.id ? 'color-mix(in srgb, var(--accent) 12%, var(--surface))' : 'var(--bg)'}"
									onclick={() => selectItem(item)}
									role="treeitem"
									aria-selected={selectedId === item.id}
									tabindex="0"
									onkeydown={(e) => {
										if (e.key === 'Enter') selectItem(item);
									}}
								>
									{#if item.children.length > 0}
										<button
											type="button"
											class="rounded p-0.5"
											style="color: var(--muted)"
											onclick={(e) => {
												e.stopPropagation();
												toggle(item.id);
											}}
										>
											<ChevronRight
												size={14}
												style="transform: {expanded.has(item.id) ? 'rotate(90deg)' : 'none'}"
											/>
										</button>
									{:else}
										<Globe size={13} style="color: var(--muted)" />
									{/if}
									<span class="flex-1 truncate text-xs font-medium">{item.name}</span>
									<button
										type="button"
										class="rounded p-1 opacity-70 hover:opacity-100"
										style="color: var(--muted)"
										title="Add child"
										onclick={(e) => {
											e.stopPropagation();
											void addNewItem(item.id);
										}}
									>
										<Plus size={13} />
									</button>
									<button
										type="button"
										class="rounded p-1 opacity-70 hover:opacity-100"
										style="color: var(--danger)"
										title="Delete item"
										onclick={(e) => {
											e.stopPropagation();
											void removeItem(item);
										}}
									>
										<Trash2 size={13} />
									</button>
								</div>
							{/each}
						</div>
					{/if}
				</div>

				<!-- Right Pane: Selected World Item Inspector (General Info + Passion / Conflict tabs) -->
				<div
					class="flex flex-col gap-4 rounded-lg border p-4 md:col-span-7"
					style="border-color: var(--border); background: var(--surface)"
				>
					{#if !selectedItem}
						<div class="flex min-h-[260px] flex-col items-center justify-center gap-2 text-center">
							<Globe size={28} style="color: var(--muted)" />
							<p class="text-sm" style="color: var(--muted)">
								Select a world item on the left or create a new one.
							</p>
						</div>
					{:else}
						<div class="flex items-center justify-between gap-2">
							<div class="flex gap-1 rounded-lg border p-1" style="border-color: var(--border)">
								<button
									type="button"
									class="rounded px-3 py-1 text-xs font-medium"
									style="background: {activeDetailTab === 'description' ? 'var(--accent)' : 'transparent'}; color: {activeDetailTab === 'description' ? 'var(--accent-text)' : 'var(--text)'}"
									onclick={() => (activeDetailTab = 'description')}
								>
									General & Description
								</button>
								<button
									type="button"
									class="rounded px-3 py-1 text-xs font-medium"
									style="background: {activeDetailTab === 'conflict' ? 'var(--accent)' : 'transparent'}; color: {activeDetailTab === 'conflict' ? 'var(--accent-text)' : 'var(--text)'}"
									onclick={() => (activeDetailTab = 'conflict')}
								>
									Passion & Conflict
								</button>
							</div>

							<button
								type="button"
								class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium"
								style="background: var(--accent); color: var(--accent-text); opacity: {saving ? 0.7 : 1}"
								onclick={saveSelected}
								disabled={saving || !draftName.trim()}
							>
								{#if saved}<Check size={13} />{/if}
								{saving ? 'Saving...' : 'Save'}
							</button>
						</div>

						{#if activeDetailTab === 'description'}
							<div class="flex flex-col gap-3">
								<div class="flex flex-col gap-1">
									<label for="world-name" class="text-xs font-medium" style="color: var(--muted)">Name</label>
									<input
										id="world-name"
										class="rounded-lg border px-3 py-2 text-sm"
										style="background: var(--bg); border-color: var(--border); color: var(--text)"
										bind:value={draftName}
										oninput={() => (saved = false)}
										placeholder="World element name"
									/>
								</div>
								<div class="flex flex-col gap-1">
									<label for="world-description" class="text-xs font-medium" style="color: var(--muted)">
										Description
									</label>
									<textarea
										id="world-description"
										class="w-full rounded-lg border px-3 py-2 text-sm"
										rows={10}
										style="background: var(--bg); border-color: var(--border); color: var(--text); resize: vertical"
										bind:value={draftDescription}
										oninput={() => (saved = false)}
										placeholder="Describe this place, culture, rule, or object..."
									></textarea>
								</div>
							</div>
						{:else}
							<div class="flex flex-col gap-3">
								<div class="flex flex-col gap-1">
									<label for="world-passion" class="text-xs font-medium" style="color: var(--muted)">
										Source of Passion
									</label>
									<textarea
										id="world-passion"
										class="w-full rounded-lg border px-3 py-2 text-sm"
										rows={5}
										style="background: var(--bg); border-color: var(--border); color: var(--text); resize: vertical"
										bind:value={draftPassion}
										oninput={() => (saved = false)}
										placeholder="What inspires passion or devotion in this aspect of the world?"
									></textarea>
								</div>
								<div class="flex flex-col gap-1">
									<label for="world-conflict" class="text-xs font-medium" style="color: var(--muted)">
										Source of Conflict
									</label>
									<textarea
										id="world-conflict"
										class="w-full rounded-lg border px-3 py-2 text-sm"
										rows={5}
										style="background: var(--bg); border-color: var(--border); color: var(--text); resize: vertical"
										bind:value={draftConflict}
										oninput={() => (saved = false)}
										placeholder="How does this element generate tension or conflict in the story?"
									></textarea>
								</div>
							</div>
						{/if}
					{/if}
				</div>
			</div>
		{/if}
	</div>
</AppShell>
