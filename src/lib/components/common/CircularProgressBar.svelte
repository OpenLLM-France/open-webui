<script lang="ts">
	// Imports
	import { Doughnut } from 'svelte-chartjs';
	import { Chart as ChartJS, ArcElement, CategoryScale } from 'chart.js';

	export let progress = 0; // How much should the progress bar be filled (%)

	// Set up data
	const data = {
		datasets: [
			{
				data: [progress, 100 - progress]
			}
		]
	};

	// Set up chart parameters
	const options = {
		responsive: true,
		backgroundColor: ['#262626', '#EEE'],
		hoverBackgroundColor: ['#262626', '#EEE'],
		borderColor: 'transparent',
		circumference: 300,
		rotation: 210,
		borderRadius: 1000,
		cutout: 90
	};

	ChartJS.register(ArcElement, CategoryScale);
</script>

<Doughnut {data} {options} />
