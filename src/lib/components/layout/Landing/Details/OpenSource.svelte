<script lang="ts">
	// Import translation utility and global store
	import i18n from '$lib/i18n';
	import { WEBUI_NAME } from '$lib/stores';

	// Import icons
	import EyeInBox from '$lib/components/icons/EyeInBox.svelte';
	import StateGraph from '$lib/components/icons/StateGraph.svelte';
	import TouchWindow from '$lib/components/icons/TouchWindow.svelte';
</script>

<div class="px-8 md:px-12 xl:px-24 2xl:px-48 py-12 xl:py-16 2xl:py-24">
	<div class="text-2xl xl:text-3xl mb-8 xl:mb-16">
		{$i18n.t('What makes {{WEBUI_NAME}} truly Open Source ?', { WEBUI_NAME: $WEBUI_NAME })}
	</div>
	<div class="grid gap-12 md:grid-cols-2 lg:grid-cols-3 xl:gap-16 2xl:gap-24">
		<div
			class="flex flex-col space-y-4
			 	bg-fixed bg-gradient-to-br from-blue-50 to-red-50 shadow-md p-8
			 	2xl:space-y-6"
		>
			<EyeInBox className="size-10" />
			<span class="text-xl font-medium xl:text-2xl">
				{$i18n.t('Transparent Data')}
			</span>
			<span class="text-justify">
				{$i18n.t(
					'All training datasets are openly available and licensed for public use. We ensure transparency at every stage, from collection to curation.'
				)}
			</span>
		</div>
		<div
			class="flex flex-col space-y-4
			 	bg-fixed bg-gradient-to-br from-blue-50 to-red-50 shadow-md p-8
			 	2xl:space-y-6"
		>
			<StateGraph className="size-10" />
			<span class="text-xl font-medium xl:text-2xl">
				{$i18n.t('Open Algorithms')}
			</span>
			<span class="text-justify">
				{$i18n.t(
					'Our training methodologies, fine-tuning processes, and "secret sauce" are thoroughly documented and openly accessible for anyone to explore, use, and improve.'
				)}
			</span>
		</div>
		<div
			class="flex flex-col space-y-4
			 	bg-fixed bg-gradient-to-br from-blue-50 to-red-50 shadow-md p-8
			 	2xl:space-y-6"
		>
			<TouchWindow className="size-10 p-[0.125rem]" />
			<span class="text-xl font-medium xl:text-2xl">
				Licence libre
				<!-- {$i18n.t('A Completely Free-Access Production Line')} -->
			</span>
			<span class="text-justify">
				{$i18n.t(
					"{{WEBUI_NAME}}'s weights, checkpoints, and source code are available under the Apache 2.0 license. This permissive, unrestricted license allows anyone, anywhere in the world, to use, adapt, and deploy the model for any purpose, ensuring true global accessibility and innovation.",
					{ WEBUI_NAME: $WEBUI_NAME }
				)}
			</span>
		</div>
	</div>
</div>
