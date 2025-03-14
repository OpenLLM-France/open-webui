<script>
	// Import global stores
	import { showContactUs, showNotice, WEBUI_NAME } from '$lib/stores';

	// Import components
	import Header from '$lib/components/layout/Landing/Header.svelte';
	import Notice from '$lib/components/layout/Overlay/Notice.svelte';
	import ContactUs from '$lib/components/layout/Overlay/ContactUs.svelte';
	import Footer from '$lib/components/layout/Landing/Footer.svelte';
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<!-- Notice Popup -->
{#if $showNotice}
	<Notice />
{:else}
	<button
		class="fixed bottom-3 right-4 flex items-center justify-center h-6 aspect-square rounded-full border text-xs bg-white/80 hover:bg-gray-100/80 transition-all"
		on:click={() => {
			$showNotice = true;
		}}
	>
		?
	</button>
{/if}

<!-- Contact Us Form Popup -->
{#if $showContactUs}
	<ContactUs bind:show={$showContactUs} isLightMode={true} />
{/if}

<Header />

<!-- Page -->
<div class="h-screen overflow-y-scroll text-gray-700">
	<slot />

	<Footer />
</div>
