<script lang="ts">
	import { userSignOut } from '$lib/apis/auths';
	import i18n from '$lib/i18n';
	import { endTimestamp, termsOfUse } from '$lib/stores';
	import { onMount } from 'svelte';

	const SECOND: number = 1000;
	const MINUTE: number = 60 * SECOND;
	const DEFAULT_DURATION: number = 2 * MINUTE;

	let timeRemaining: number;

	const formatTime = (timestamp: number) => {
		const minutes = Math.floor(timestamp / MINUTE);
		const seconds = Math.floor((timestamp % MINUTE) / SECOND);
		if (minutes === 0) return `${seconds}s`;
		else if (seconds === 0) return `${minutes}min`;
		else return `${minutes}min ${seconds}s`;
	};

	onMount(() => {
		if ($endTimestamp === -1) $endTimestamp = Date.now() + DEFAULT_DURATION;

		timeRemaining = $endTimestamp - Date.now();

		const timer = setInterval(() => {
			timeRemaining -= SECOND;
			if (timeRemaining <= 0) {
				clearInterval(timer);
				userSignOut();
				$endTimestamp = -1;
				termsOfUse.reset();
				localStorage.removeItem('token');
				location.href = '/auth';
			}
		}, SECOND);
	});
</script>

<div
	class="fixed top-3 right-1/2 translate-x-1/2 flex items-center space-x-3 bg-[#ffffff55] border px-5 py-3 rounded-lg shadow-md z-50
	{timeRemaining < MINUTE ? 'border-red-500 border-2 text-red-500 font-bold' : ''} "
>
	<svg
		xmlns="http://www.w3.org/2000/svg"
		height="24px"
		viewBox="0 -960 960 960"
		width="24px"
		fill="currentColor"
		class={timeRemaining < MINUTE ? 'fill-red-500' : ''}
	>
		<path
			d="M360-840v-80h240v80H360Zm80 440h80v-240h-80v240Zm40 320q-74 0-139.5-28.5T226-186q-49-49-77.5-114.5T120-440q0-74 28.5-139.5T226-694q49-49 114.5-77.5T480-800q62 0 119 20t107 58l56-56 56 56-56 56q38 50 58 107t20 119q0 74-28.5 139.5T734-186q-49 49-114.5 77.5T480-80Zm0-80q116 0 198-82t82-198q0-116-82-198t-198-82q-116 0-198 82t-82 198q0 116 82 198t198 82Zm0-280Z"
		/>
	</svg>
	<span class="text-sm w-48">
		{$i18n.t('Time remaining')} : {formatTime(timeRemaining)}
	</span>
</div>
