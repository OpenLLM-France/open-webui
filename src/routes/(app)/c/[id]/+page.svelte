<script lang="ts">
	import { page } from '$app/stores';

	import Chat from '$lib/components/chat/Chat.svelte';
	import Help from '$lib/components/layout/Help.svelte';
	import TermsOfUse from '$lib/components/TermsOfUse.svelte';
</script>

<Help />
<TermsOfUse />
<Chat chatIdProp={$page.params.id} />
