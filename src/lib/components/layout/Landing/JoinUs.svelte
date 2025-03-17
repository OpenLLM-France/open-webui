<script>
	// Import translation utility and global store
	import i18n from '$lib/i18n';
	import { WEBUI_NAME } from '$lib/stores';
</script>

<div class="px-8 md:px-12 xl:px-24 2xl:px-48 py-12 xl:py-24">
	<div class="flex flex-col space-y-4 mb-8 xl:mb-16">
		<span class="text-2xl xl:text-3xl">
			{$i18n.t('Join the {{WEBUI_NAME}} movement', { WEBUI_NAME: $WEBUI_NAME })}
		</span>
		<span class="text-sm leading-6">
			{$i18n.t(
				"{{WEBUI_NAME}} is more than a model - it's a community-driven effort to redefine the future of AI. By joining us, you contribute to building AI that aligns with our shared values of openness, transparency, and trust.",
				{ WEBUI_NAME: $WEBUI_NAME }
			)}
		</span>
	</div>
	<div class="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
		<a
			class="shiny-card hover:scale-[102.5%] transition-all"
			href="https://github.com/OpenLLM-France"
		>
			<div class="flex justify-center items-center xl:h-48 2xl:h-64 xl:p-4">
				<img
					crossorigin="anonymous"
					src="/assets/logos/github.png"
					class="h-28 2xl:h-36"
					alt="GitHub logo"
				/>
			</div>
			<span
				class="px-4 pb-2 text-xl lg:text-center xl:text-left 2xl:text-2xl xl:min-h-16 2xl:min-h-18"
			>
				{$i18n.t('Collaborate on GitHub')}
			</span>
			<span class="px-4 text-sm md:h-10 lg:text-center xl:text-left xl:h-16 2xl:h-32">
				{$i18n.t("Contribute to {{WEBUI_NAME}}'s development.", { WEBUI_NAME: $WEBUI_NAME })}
			</span>
			<a
				href="https://github.com/OpenLLM-France"
				class="my-6 py-3 px-12 self-center rounded-full bg-gradient-to-br from-blue-100 to-red-100 hover:from-blue-200 hover:to-red-200 hover:text-gray-800 -all"
			>
				{$i18n.t('Contribute')}
			</a>
		</a>
		<a
			class="shiny-card hover:scale-[102.5%] transition-all"
			href="https://huggingface.co/OpenLLM-France"
		>
			<div class="flex justify-center items-center xl:h-48 2xl:h-64 xl:p-4">
				<img
					crossorigin="anonymous"
					src="/assets/logos/lucie.svg"
					class="h-36 2xl:h-48"
					alt="Lucie illustration"
				/>
			</div>
			<span
				class="px-4 pb-2 text-xl lg:text-center xl:text-left 2xl:text-2xl xl:min-h-16 2xl:min-h-18"
			>
				{$i18n.t('Experiment on Hugging Face')}
			</span>
			<span class="px-4 text-sm lg:text-center xl:text-left xl:h-16 2xl:h-32">
				{$i18n.t("Explore {{WEBUI_NAME}}'s capabilities in your projects.", {
					WEBUI_NAME: $WEBUI_NAME
				})}
			</span>
			<a
				href="https://huggingface.co/OpenLLM-France"
				class="my-6 py-3 px-12 self-center rounded-full bg-gradient-to-br from-blue-100 to-red-100 hover:from-blue-200 hover:to-red-200 hover:text-gray-800 -all"
			>
				{$i18n.t('Experiment')}
			</a>
		</a>
		<a class="shiny-card hover:scale-[102.5%] transition-all" href="https://www.openllm-france.fr/">
			<div class="flex justify-center items-center xl:h-48 2xl:h-64 xl:p-4">
				<img
					crossorigin="anonymous"
					src="/assets/logos/openllm-france.png"
					class="h-32 2xl:h-40"
					alt="OpenLLM France Logo"
				/>
			</div>
			<span
				class="px-4 pb-2 text-xl lg:text-center xl:text-left 2xl:text-2xl xl:min-h-16 2xl:min-h-18"
			>
				{$i18n.t('Be Part of OpenLLM France')}
			</span>
			<span class="px-4 text-sm lg:text-center xl:text-left xl:h-16 2xl:h-32">
				{$i18n.t('Join the growing community dedicated to sovereign and open AI.')}
			</span>
			<a
				href="https://www.openllm-france.fr/"
				class="my-6 py-3 px-12 self-center rounded-full bg-gradient-to-br from-blue-100 to-red-100 hover:from-blue-200 hover:to-red-200 hover:text-gray-800 -all"
			>
				{$i18n.t('Join us')}
			</a>
		</a>
		<a
			class="shiny-card hover:scale-[102.5%] transition-all"
			href="https://github.com/OpenLLM-Europe/European-OpenLLM-Projects"
		>
			<div class="flex justify-center items-center xl:h-48 2xl:h-64 xl:p-4">
				<img
					crossorigin="anonymous"
					src="/assets/logos/openllm-europe.png"
					class="h-32 2xl:h-40"
					alt="OpenLLM Europe logo"
				/>
			</div>
			<span
				class="px-4 pb-2 text-xl lg:text-center xl:text-left 2xl:text-2xl xl:min-h-16 2xl:min-h-18"
			>
				{$i18n.t('Other European Initiatives')}
			</span>
			<span class="px-4 text-sm lg:text-center xl:text-left xl:h-16 2xl:h-32">
				{$i18n.t('Explore other european OpenLLM projects.')}
			</span>
			<a
				href="https://github.com/OpenLLM-Europe/European-OpenLLM-Projects"
				class="my-6 py-3 px-12 self-center rounded-full bg-gradient-to-br from-blue-100 to-red-100 hover:from-blue-200 hover:to-red-200 hover:text-gray-800 -all"
			>
				{$i18n.t('Explore')}
			</a>
		</a>
	</div>
</div>
