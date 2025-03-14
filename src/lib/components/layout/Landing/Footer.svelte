<script>
	// Import translation utility
	import i18n from '$lib/i18n';
</script>

<footer class="px-8 md:px-12 xl:px-24 2xl:px-48 flex flex-col items-center space-y-6 mb-8">
	<div class="h-px w-full my-4 bg-gray-300" />
	<img
		crossorigin="anonymous"
		src="/assets/logos/openllm-france-horizontal.svg"
		class="h-16"
		alt="OpenLLM France logo"
	/>
	<div class="flex flex-col items-center space-y-2">
		<span class="text-xs">2025 - {$i18n.t('All rights reserved')} ©</span>
		<div class="text-[0.6rem]">
			<a href="https://linagora.com/fr/legal" class="underline hover:text-violet-500">
				{$i18n.t('Terms of Use')}
			</a>
			-
			<a href="https://linagora.com/fr/privacy" class="underline hover:text-violet-500">
				{$i18n.t('Privacy Policy')}
			</a>
		</div>
	</div>
</footer>
