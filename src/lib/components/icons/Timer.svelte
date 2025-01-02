<script lang="ts">
	import { userSignOut } from '$lib/apis/auths';
	import { termsOfUse, timeRemaining } from '$lib/stores';
	import { onMount } from 'svelte';

	const MINUTE: number = 60;
	const DEFAULT_TIME: number = 15 * MINUTE;

	const timer = setInterval(() => {
		$timeRemaining -= 1;
		if ($timeRemaining <= 0) {
			clearInterval(timer);
			setTimeout(() => {
				alert('You ran out of time');
				userSignOut();
				termsOfUse.reset();
				localStorage.removeItem('token');
				location.href = '/auth';
			}, 25); // To ensure the timer is visually 0
		}
	}, 1000);

	const formatTime = (seconds: number) => {
		const minutes = Math.floor(seconds / 60); // Calculate the number of minutes
		const remainingSeconds = seconds % 60; // Calculate the remaining seconds
		if (minutes > 0) return `${minutes}min ${remainingSeconds}s`;
		else return `${remainingSeconds}s`;
	};

	onMount(() => {
		if ($timeRemaining === -1) $timeRemaining = DEFAULT_TIME;
	});
</script>

<div class="flex items-center space-x-2">
	<svg
		xmlns="http://www.w3.org/2000/svg"
		height="24px"
		viewBox="0 -960 960 960"
		width="24px"
		fill="currentColor"
	>
		<path
			d="M360-840v-80h240v80H360Zm80 440h80v-240h-80v240Zm40 320q-74 0-139.5-28.5T226-186q-49-49-77.5-114.5T120-440q0-74 28.5-139.5T226-694q49-49 114.5-77.5T480-800q62 0 119 20t107 58l56-56 56 56-56 56q38 50 58 107t20 119q0 74-28.5 139.5T734-186q-49 49-114.5 77.5T480-80Zm0-80q116 0 198-82t82-198q0-116-82-198t-198-82q-116 0-198 82t-82 198q0 116 82 198t198 82Zm0-280Z"
		/>
	</svg>
	<span class="text-sm w-48">
		Time remaining : <span class={$timeRemaining < MINUTE ? 'text-red-700' : ''}>
			{formatTime($timeRemaining)}
		</span>
	</span>
</div>
