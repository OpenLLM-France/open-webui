<script lang="ts">
	// Imports
	import { getContext } from 'svelte';
	import { WEBUI_NAME, showSidebar, subscriptionInfo } from '$lib/stores';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { getSubscriptionInfo } from '$lib/apis/stripe';

	const i18n = getContext('i18n'); // Translations

	// Call API to retrieve subscription information
	getSubscriptionInfo().then((info) => subscriptionInfo.set(info));
</script>

<!-- Page title -->
<svelte:head>
	<title>
		{$i18n.t('API Usage')} | {$WEBUI_NAME}
	</title>
</svelte:head>

<div class="w-full h-screen max-h-[100dvh] {$showSidebar ? 'md:max-w-[calc(100%-260px)]' : ''}">
	<!-- Open menu button for mobile -->
	<div class="fixed w-full px-2.5 py-1 backdrop-blur-xl bg-white dark:bg-gray-900">
		<div class=" flex items-center">
			<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
				<button
					id="sidebar-toggle-button"
					class="cursor-pointer p-1.5 flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
					on:click={() => {
						showSidebar.set(!$showSidebar);
					}}
					aria-label="Toggle Sidebar"
				>
					<div class=" m-auto self-center">
						<MenuLines />
					</div>
				</button>
			</div>
		</div>
	</div>

	<div class="flex-1 max-h-full overflow-y-auto py-12 bg-white dark:bg-gray-900 px-16">
		<slot />
	</div>
</div>
