<script>
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
	import zoomPlugin from 'chartjs-plugin-zoom';

	const data = {
		labels: ['10/12', '11/12', '12/12', '13/12', '14/12', '15/12'],
		datasets: [
			{
				label: 'Prompt tokens',
				data: [8, 8, 7, 6, 8, 9],
				borderColor: '#0000FF',
				fill: true,
				backgroundColor: '#0000FF55'
			},
			{
				label: 'Response tokens',
				data: [5, 8, 9, 10, 7, 7],
				borderColor: '#FF0000',
				fill: true,
				backgroundColor: '#FF000055'
			}
		]
	};

	const options = {
		responsive: true,
		borderWidth: 1,
		tension: 0.5,
		pointHitRadius: 50,
		pointRadius: 0,
		plugins: {
			zoom: {
				zoom: {
					wheel: {
						enabled: true
					},
					pinch: {
						enabled: true
					},
					mode: 'x'
				}
			},
			limits: { y: { min: 'original', max: 'original' } }
		}
	};

	ChartJS.register(
		Tooltip,
		LineElement,
		LinearScale,
		PointElement,
		CategoryScale,
		Filler,
		zoomPlugin
	);
</script>

<Line {data} {options} />
