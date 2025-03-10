<script lang="ts">
	// Import translation utility
	import i18n from '$lib/i18n';

	// Import components
	import LanguageSelector from '../LanguageSelector.svelte';

	/** Controls contact form visibility */
	export let showContactUs: boolean;
</script>

<header
	aria-label="Site header"
	class="fixed z-30 w-full h-20 px-8 flex items-center justify-between
        border-b-[2px] border-gray-100/50 bg-white/70 backdrop-blur-md
        md:px-12 xl:px-24 2xl:px-48"
>
	<!-- Logo and language selector -->
	<div class="relative h-full flex items-center space-x-4">
		<img
			crossorigin="anonymous"
			loading="eager"
			fetchpriority="high"
			src="/assets/logos/lucie-with-text.svg"
			class="h-full py-1"
			alt="OpenLLM France logo"
			width="auto"
			height="100%"
		/>
		<LanguageSelector isLightMode={true} isInHorizontalNavbar={true} />
	</div>

	<!-- Contact button -->
	<button
		class="w-auto h-8 px-3 rounded-full border border-slate-300 bg-transparent
            text-sm text-slate-500 transition-all hover:bg-white hover:text-slate-600
            md:h-12 md:px-8 xl:h-14 xl:px-12 xl:text-base"
		on:click={() => (showContactUs = !showContactUs)}
		aria-expanded={showContactUs}
		aria-controls="contact-form"
		aria-label={$i18n.t('Contact us')}
	>
		{$i18n.t('Contact us')}
	</button>
</header>
