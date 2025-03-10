<script lang="ts">
	// Import translation utility and global store
	import i18n from '$lib/i18n';
	import { WEBUI_NAME } from '$lib/stores';
	import Description from './About/Description.svelte';

	// Import components
	import Logos from './About/Logos.svelte';
	import YouTube from './About/YouTube.svelte';
</script>

<!-- About section with gradient background and responsive grid layout -->
<section
	class="p-8 md:p-12 xl:p-24 2xl:px-48 space-y-4
		bg-gradient-to-r from-blue-50 from-40% via-white to-60% to-red-50"
	aria-labelledby="about-section"
>
	<div class="grid xl:grid-cols-2">
		<!-- Left column -->
		<div class="flex flex-col justify-center items-start space-y-6 pr-24">
			<!-- Main title -->
			<h1 id="about-title" class="text-2xl max-xl:text-center xl:text-3xl 2xl:text-[2.5rem]">
				{$i18n.t(
					'{{WEBUI_NAME}} — The truly open source AI built on transparency, trust, and efficiency.',
					{ WEBUI_NAME: $WEBUI_NAME }
				)}
			</h1>

			<!-- Subtitle/tagline -->
			<h2 class="pb-2 text-lg text-gray-500 max-xl:text-center xl:text-xl 2xl:text-2xl">
				{$i18n.t('Beyond openness, we pioneer transparency and trust.')}
			</h2>

			<!-- Description paragraph -->
			<p class="text-base text-justify max-xl:text-center xl:text-lg">
				{$i18n.t(
					"{{WEBUI_NAME}} isn't just open, it's exceptionally transparent and reliable. From its inception, every decision has been guided by principles of trustworthiness, fairness, and accountability. Whether it's for education, government, or research, {{WEBUI_NAME}} is designed to be a model you can count on.",
					{ WEBUI_NAME: $WEBUI_NAME }
				)}
			</p>

			<!-- Sign in button -->
			<button
				class="rounded-full mt-4 px-8 py-4 bg-blue-500 text-white hover:bg-blue-600 transition-all"
			>
				{$i18n.t('Sign in')}
			</button>
		</div>

		<!-- Right column -->
		<div class="flex items-center justify-end pl-24">
			<!-- Mascot image with responsive sizing and optimization -->
			<img
				crossorigin="anonymous"
				src="/assets/images/lucie.png"
				srcset="/assets/images/lucie.png 1x, /assets/images/lucie@2x.png 2x"
				width="500"
				height="500"
				loading="lazy"
				class="h-full w-fit md:max-h-[50vh] md:mt-8 xl:max-h-[85vh]"
				alt="Lucie, the mascot representing our transparent and trustworthy AI assistant"
			/>
		</div>
	</div>

	<!-- List of partner logos -->
	<Logos />

	<!-- Youtube video explaining what LUCIE is -->
	<YouTube />

	<Description />
</section>
