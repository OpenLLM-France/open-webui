<script>
	// Import translation utility and global store
	import i18n from '$lib/i18n';
	import { WEBUI_NAME } from '$lib/stores';
</script>

<div class="px-8 md:px-12 xl:px-24 2xl:px-48 my-12 xl:my-24">
	<div class="text-2xl xl:text-3xl mb-8 xl:mb-16">
		{$i18n.t('{{WEBUI_NAME}} in figures', { WEBUI_NAME: $WEBUI_NAME })}
	</div>
	<div
		class="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-8 xl:gap-16 2xl:gap-24"
	>
		<div class="flex flex-col space-y-3 xl:space-y-6">
			<span class="text-xl font-medium text-center self-center xl:text-2xl h-14 xl:h-20 flex items-end">
				{$i18n.t('7 billion parameters')}
			</span>
			<div class="w-full h-px bg-black"></div>
			<span class="text-sm text-justify xl:text-base">
				{$i18n.t(
					'Model size: 7 billion parameters - compact and optimized for performance across diverse applications. In 2025, we will build a more compact model size of {{WEBUI_NAME}} (<3B).',
					{ WEBUI_NAME: $WEBUI_NAME }
				)}
			</span>
		</div>
		<div class="flex flex-col space-y-3 xl:space-y-6">
			<span class="text-xl font-medium text-center self-center xl:text-2xl h-14 xl:h-20 flex items-end"
				>{$i18n.t('3.1 trillion tokens')}</span
			>
			<div class="w-full h-px bg-black"></div>
			<span class="text-sm text-justify xl:text-base">
				{$i18n.t(
					'Training Dataset: 3.1 trillion tokens, carefully curated to balance quality and diversity, including French, English, German, Spanish, Italian, and code.'
				)}
			</span>
		</div>
		<div class="flex flex-col space-y-3 xl:space-y-6">
			<span class="text-xl font-medium text-center self-center xl:text-2xl h-14 xl:h-20 flex items-end">
				{$i18n.t('600k GPU Hours')}
			</span>
			<div class="w-full h-px bg-black"></div>
			<span class="text-sm text-justify xl:text-base">
				{$i18n.t(
					'Training Hours: Over 600,000 GPU hours on the Jean Zay supercomputer, utilizing 512 NVIDIA H100 GPUs in parallel.'
				)}
			</span>
		</div>
		<div class="flex flex-col space-y-3 xl:space-y-6">
			<span class="text-xl font-medium text-center self-center xl:text-2xl h-14 xl:h-20 flex items-end">
				{$i18n.t('Languages supported')}
			</span>
			<div class="w-full h-px bg-black"></div>
			<span class="text-sm text-justify xl:text-base">
				{$i18n.t(
					'Multilingual focus, with a primary emphasis on French and main european languages, ensuring cultural and linguistic representation.'
				)}
			</span>
		</div>
		<div class="flex flex-col space-y-3 xl:space-y-6">
			<span class="text-xl font-medium text-center self-center xl:text-2xl h-14 2xl:h-20 flex items-end">2023 - 2025</span>
			<div class="w-full h-px bg-black"></div>
			<span class="text-sm text-justify xl:text-base">
				{$i18n.t(
					"Development Timeline : Training initiated in late 2023, culminating with the model's release in January 2025."
				)}
			</span>
		</div>
	</div>
</div>
