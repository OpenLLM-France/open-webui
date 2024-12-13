<script lang="ts">
	// Imports
	import { getContext } from 'svelte';
	import CircularProgressBar from '$lib/components/common/CircularProgressBar.svelte';
	import Coins from '$lib/components/icons/Coins.svelte';
	import AreaLineChart from '$lib/components/common/AreaLineChart.svelte';

	const i18n = getContext('i18n'); // Translations

	// Token data
	export let tokensLeft = 700;
	export let totalTokens = 800;
</script>

<div class="flex flex-col">
	<!-- Token usage -->
	<h1 class="pb-12 text-4xl font-bold">{$i18n.t('API Usage')}</h1>
	<div class="md:flex md:space-x-12 max-md:space-y-12">
		<div
			class="bg-gray-50 dark:bg-gray-950 lg:w-72 md:h-96 rounded-3xl flex flex-col items-center p-6"
		>
			<!-- Tokens left -->
			<h2 class="font-semibold">{$i18n.t('Tokens left')}</h2>
			<div class="w-64 h-64 p-6 relative">
				<CircularProgressBar progress={(tokensLeft / totalTokens) * 100} />
				<div
					class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center"
				>
					<div
						class="bg-gray-100 p-1.5 mb-2 aspect-square flex items-center justify-center rounded-full"
					>
						<Coins className="size-6" />
					</div>
					<span class="font-bold text-3xl"> {tokensLeft} </span>
					<span class="font-medium text-sm"> / {totalTokens} </span>
				</div>
			</div>
			<button
				class="bg-gray-100 rounded-full font-medium px-8 py-3 text-sm hover:bg-gray-200 transition"
			>
				{$i18n.t('Buy more')}
			</button>
		</div>

		<!-- Tokens spent -->
		<div
			class="bg-gray-50 dark:bg-gray-950 grow md:h-96 rounded-3xl flex flex-col items-center p-6"
		>
			<h2 class="font-semibold">{$i18n.t('Tokens spent')}</h2>
			<span class="text-xs">Dec. 10 - Dec. 15</span>

			<div class="w-full h-full p-6 relative flex flex-col items-center">
				<AreaLineChart />
				<div class="flex text-xs items-center space-x-2">
					<div class="rounded-full h-2 aspect-square bg-[#FF000055]"></div>
					<span>Prompt tokens</span>
					<div class="w-8" />
					<div class="rounded-full h-2 aspect-square bg-[#0000FF55]"></div>
					<span>Response tokens</span>
				</div>
			</div>
		</div>
	</div>
</div>
