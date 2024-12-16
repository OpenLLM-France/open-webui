<script lang="ts">
	// Imports
	import { Line } from 'svelte-chartjs';
	import {
		Chart as ChartJS,
		Tooltip,
		LineElement,
		LinearScale,
		PointElement,
		CategoryScale,
		Filler
	} from 'chart.js';
	import { onMount } from 'svelte';
	import type { LineChartDataset } from './types';
	import { colors } from './colors';

	export let labels: Array<string> = []; // X-Axis
	export let datasets: Array<LineChartDataset> = []; // Y-Axis (multiple lines supported)

	// Set up data
	const data = {
		labels,
		datasets: [{}]
	};

	// Add custom parameters to the datasets
	datasets.forEach((dataset, i) => {
		data.datasets.push({
			...dataset,
			borderColor: colors[i % colors.length],
			fill: true,
			backgroundColor: colors[i] + '33'
		});
	});

	// Set up chart parameters
	const options = {
		responsive: true,
		borderWidth: 1,
		tension: 0.5, // Smoothes the curve; however, on Chrome-based browsers, the background may have some holes if this is enabled
		pointHitRadius: 50,
		pointRadius: 0,
		aspectRatio: 2,
		scales: {
			x: {
				border: { display: false },
				grid: {
					color: '#E5E5E5'
				},
				ticks: {
					font: { size: 11 }
				}
			},
			y: {
				border: { display: false },
				grid: {
					display: false
				},
				ticks: {
					display: false
				}
			}
		}
	};

	// Set up chart
	ChartJS.register(Tooltip, LineElement, LinearScale, PointElement, CategoryScale, Filler);

	/* Dynamically update the aspect ratio to match parent div */
	const updateAspectRatio = () => {
		const chartParentDiv = document.getElementById('chart')?.parentNode as HTMLDivElement;
		const h = chartParentDiv?.clientHeight - 36;
		const w = chartParentDiv?.clientWidth;
		options.aspectRatio = Math.max(w / h, 1.5); // Ensure minimum width
	};

	// On page load
	onMount(() => {
		const chartParentDiv = document.getElementById('chart')?.parentNode as HTMLDivElement;

		// On window resize, update aspect ratio
		const resizeObserver: ResizeObserver = new ResizeObserver(() => {
			updateAspectRatio();
		});
		resizeObserver.observe(chartParentDiv);

		// Sometimes above resizer won't work, add this one to ensure at least one does
		// Will need to find the cause of the problem to fix it and have cleaner code without duplication
		window.addEventListener('resize', updateAspectRatio);
	});

	$: updateAspectRatio();
</script>

<div id="chart" class="h-full w-full flex justify-center">
	<Line {data} {options} />
</div>
