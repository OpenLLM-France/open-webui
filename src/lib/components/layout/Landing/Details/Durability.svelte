<script lang="ts">
	// Import translation utility and global store
	import i18n from '$lib/i18n';
	import { WEBUI_NAME } from '$lib/stores';

	// Import icons
	import EuLogo from '$lib/components/icons/EULogo.svelte';
	import Speedometer from '$lib/components/icons/Speedometer.svelte';
	import PlanetLeaf from '$lib/components/icons/PlanetLeaf.svelte';
</script>

<div
	class="px-8 md:px-12 xl:px-24 2xl:px-48 py-12 xl:py-24 bg-gradient-to-br from-indigo-50 to-75% to-green-50 bg-fixed"
>
	<div class="grid 2xl:grid-cols-2 items-center mb-8 xl:mb-24">
		<span class="text-2xl xl:text-3xl">
			{$i18n.t('Designed for sovereignty and sustainability')}
		</span>
		<span class="text-sm">
			{$i18n.t(
				'{{WEBUI_NAME}} was built to address the unique challenges of developing ethical, efficient, and accessible AI.',
				{ WEBUI_NAME: $WEBUI_NAME }
			)}
		</span>
	</div>
	<div class="grid gap-6 md:grid-cols-2 md:gap-12 lg:grid-cols-3 xl:gap-20 -m-8">
		<div
			class="p-8 flex flex-col space-y-4 xl:space-y-8 bg-transparent rounded transition-all hover:scale-[102.5%] hover:shadow-md"
		>
			<EuLogo className="size-16 p-1 border-2 border-gray-700 rounded-full" />
			<span class="text-2xl 2xl:text-3xl font-medium">{$i18n.t('European Sovereignty')}</span>
			<span class="text-justify">
				{$i18n.t(
					'{{WEBUI_NAME}} embodies a commitment to European values by respecting cultural diversity, promoting ethical AI development and ensuring compliance with the AI Act.',
					{ WEBUI_NAME: $WEBUI_NAME }
				)}
			</span>
		</div>
		<div
			class="p-8 flex flex-col space-y-4 xl:space-y-8 bg-transparent rounded transition-all hover:scale-[102.5%] hover:shadow-md"
		>
			<Speedometer className="size-16" />
			<span class="text-2xl 2xl:text-3xl font-medium">{$i18n.t('Compact and Efficient')}</span>
			<span class="text-justify">
				{$i18n.t(
					'Optimized for low-resource environments, {{WEBUI_NAME}}\'s architecture enables deployment on "GPU poor" infrastructures and even on mobile devices.',
					{ WEBUI_NAME: $WEBUI_NAME }
				)}
			</span>
		</div>
		<div
			class="p-8 flex flex-col space-y-4 xl:space-y-8 bg-transparent rounded transition-all hover:scale-[102.5%] hover:shadow-md"
		>
			<PlanetLeaf className="size-16" />
			<span class="text-2xl 2xl:text-3xl font-medium">{$i18n.t('Eco-Responsibility')}</span>
			<span class="text-justify">
				{$i18n.t(
					'By focusing on quality over quantity in training data, we ensure a lighter environmental footprint without compromising performance.'
				)}
			</span>
		</div>
	</div>
</div>
