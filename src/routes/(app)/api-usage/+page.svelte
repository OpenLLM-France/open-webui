<script lang="ts">
	// Imports
	import { getContext } from 'svelte';
	import CircularProgressBar from '$lib/components/common/CircularProgressBar.svelte';
	import Coins from '$lib/components/icons/Coins.svelte';

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
			class="bg-gray-50 dark:bg-gray-950 lg:w-72 h-96 rounded-3xl flex flex-col items-center p-6"
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
		<div class="bg bg-gray-50 dark:bg-gray-950 grow h-96 rounded-3xl"></div>
	</div>
</div>
