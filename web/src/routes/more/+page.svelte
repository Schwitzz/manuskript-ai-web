<script lang="ts">
import AppShell from '#lib/components/AppShell.svelte';
import { auth } from '#lib/stores/auth.svelte.ts';
import { LogOut } from '@lucide/svelte';
</script>

<AppShell title="More">
<button
class="flex w-full items-center gap-3 rounded-lg border px-4"
style="background: var(--surface); border-color: var(--border)"
onclick={() => auth.logout()}
>
<LogOut size={20} /> Log out
</button>
</AppShell>
