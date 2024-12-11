<script lang="ts">
	import { onMount } from 'svelte';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import Sidebar from '$lib/components/common/Sidebar.svelte';

	let stripeScriptLoaded = false;

	// Dynamically load Stripe script
	onMount(() => {
		if (!stripeScriptLoaded) {
			const script = document.createElement('script');
			script.src = 'https://js.stripe.com/v3/pricing-table.js';
			script.async = true;
			document.body.appendChild(script);
			script.onload = () => {
				stripeScriptLoaded = true;
			};
		}
	});
</script>

<svelte:head>
	<title>Choose Your Plan | YourSiteName</title>
</svelte:head>

{#if stripeScriptLoaded}
	<!-- Ensure Stripe script is loaded before rendering -->
	<div
		class="flex flex-col w-full h-screen max-h-[100dvh] md:max-w-[calc(100%-260px)] bg-white dark:bg-gray-900"
	>
		<div class="flex flex-col flex-auto justify-center py-8">
			<div class="px-3 w-full max-w-5xl mx-auto">
				<!-- Title and description -->
				<div class="text-3xl font-semibold line-clamp-1">Choose Your Plan</div>
				<div class="mt-1 text-gray-400">Pick a subscription plan below:</div>

				<hr class="border-gray-50 dark:border-gray-850 mt-6 mb-2" />
			</div>

			<div class="flex flex-col w-full flex-auto overflow-auto h-0">
				<!-- Stripe Pricing Table Embed -->
				<div class="h-full w-full flex flex-col py-4">
					<stripe-pricing-table
						pricing-table-id="prctbl_1QU8xSL1OXPRbGUfSQZGLM3f"
						publishable-key="pk_test_51QU8iOL1OXPRbGUft8UIzp0IDHKaxLtIpkBYrJG6P4ZaJiomiasrHCIiJuzrnm9r6kihaZ2Iq1k7n5hFS7ILztEk00BrqagIRt"
					>
					</stripe-pricing-table>
				</div>
			</div>
		</div>
	</div>
{/if}
