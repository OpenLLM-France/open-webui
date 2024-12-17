<script lang="ts">
	// Imports
	import { getContext } from 'svelte';
	import CircularProgressBar from '$lib/components/common/CircularProgressBar.svelte';
	import Coins from '$lib/components/icons/Coins.svelte';
	import AreaLineChart from '$lib/components/charts/AreaLineChart.svelte';
	import { subscriptionInfo } from '$lib/stores';

	const i18n = getContext('i18n'); // Translations

	let budgetLeft = 0;
	let budgetTotal = 10;
	// Budget spending data (note : we'll later have to fetch the data from the backend.)
	let budgetSpent = {
		timeValues: ['10/12', '11/12', '12/12', '13/12', '14/12', '15/12'],
		promptSpending: [8, 8, 7, 6, 8, 9],
		responseSpending: [5, 8, 9, 10, 7, 7]
	};

	subscriptionInfo.subscribe((info) => {
		if (info.max_budget !== undefined && info.spend !== undefined) {
			budgetLeft = info.max_budget - info.spend;
			budgetTotal = info.max_budget;
		}
	});
</script>

<div class="flex flex-col">
	<!-- Token usage -->
	<h1 class="pb-12 text-4xl font-bold">{$i18n.t('API Usage')}</h1>
	<div class="md:flex md:space-x-12 max-md:space-y-12 md:mr-12">
		<div
			class="bg-gray-50 dark:bg-gray-950 lg:w-72 md:h-96 rounded-3xl flex flex-col items-center p-6"
		>
			<!-- Tokens left -->
			<h2 class="font-semibold">{$i18n.t('Budget left')}</h2>
			<div class="w-64 h-64 p-6 relative">
				<CircularProgressBar progress={(budgetLeft / budgetTotal) * 100} />
				<div
					class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center"
				>
					<div
						class="bg-gray-100 p-1.5 mb-2 aspect-square flex items-center justify-center rounded-full"
					>
						<Coins className="size-6" />
					</div>
					<span class="font-bold text-3xl"> {budgetLeft.toFixed(2)}€ </span>
					<span class="font-medium text-xs">
						<span class="text-[0.6rem]">/</span>
						{budgetTotal.toFixed(2)}€
					</span>
				</div>
			</div>
			<button
				class="bg-gray-100 rounded-full font-medium px-8 py-3 text-sm hover:bg-gray-200 transition"
			>
				{$i18n.t('Refill')}
			</button>
		</div>

		<!-- Tokens spent -->
		<div
			class="bg-gray-50 dark:bg-gray-950 grow md:h-96 rounded-3xl flex flex-col items-center p-6"
		>
			<h2 class="font-semibold">{$i18n.t('Spending history')}</h2>
			<span class="text-xs">
				{budgetSpent.timeValues[0]} - {budgetSpent.timeValues[budgetSpent.timeValues.length - 1]}
			</span>

			<div class="w-full h-full pt-6 relative flex flex-col items-center">
				<AreaLineChart
					labels={budgetSpent.timeValues}
					datasets={[
						{ label: $i18n.t('Prompts'), data: budgetSpent.promptSpending },
						{ label: $i18n.t('Responses'), data: budgetSpent.responseSpending }
					]}
				/>
				<div class="pt-1 flex items-center space-x-2 text-xs font-medium">
					<div class="rounded-full h-2 aspect-square bg-[#FF000055]"></div>
					<span>{$i18n.t('Prompts')}</span>
					<div class="w-8" />
					<div class="rounded-full h-2 aspect-square bg-[#0000FF55]"></div>
					<span>{$i18n.t('Responses')}</span>
				</div>
			</div>
		</div>
	</div>
</div>
