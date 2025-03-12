<script lang="ts">
	// Imports
	import i18n, { getLanguages } from '$lib/i18n';
	import { locale } from '$lib/stores';
	import { onMount } from 'svelte';
	import GlobeAlt from '../icons/GlobeAlt.svelte';

	export let isLightMode = false;
	export let isInHorizontalNavbar = false;
	let opened = false;

	const changeLanguage = (code: string) => {
		$i18n.changeLanguage(code);
		$locale = code;
	};

	const toggleDropdown = (e: Event) => {
		opened = !opened;
		e.preventDefault();
		e.stopPropagation();
	};

	onMount(() => {
		window.onclick = () => {
			if (opened) opened = false;
		};
	});
</script>

<div
	class="group relative flex flex-col text-gray-900 z-20 {isLightMode ? '' : 'dark:text-gray-100'}"
>
	{#await getLanguages() then languages}
		<button class="text-left text-sm pl-2 flex items-center space-x-2" on:click={toggleDropdown}>
			<!-- <GlobeAlt /> -->
			<span>
				{(languages.find((lang) => lang.code === $i18n.language) || { title: 'Unknown' }).flag}
			</span>
			<span class={isInHorizontalNavbar ? 'max-sm:hidden' : ''}>
				{(languages.find((lang) => lang.code === $i18n.language) || { title: 'Unknown' }).title}
			</span>
		</button>
		<!-- Improve hitbox size -->
		<button class="absolute top-full h-2 w-full" on:click={toggleDropdown}></button>
		<div
			class="absolute top-full mt-2 max-h-96 max-w-32 sm:w-56 overflow-y-auto flex-col items-start space-y-2 text-xs
			bg-white/30 backdrop-blur-sm px-4 py-3 border border-slate-100/30 rounded-lg
            {isLightMode ? '' : 'dark:bg-gray-800 dark:border-gray-700'} 
            {opened ? '' : 'hidden group-hover:flex'} "
		>
			{#each languages as lang}
				<button
					class="hover:bg-white/30 hover:text-blue-600 w-full text-left p-1 rounded space-x-1
                    {isLightMode ? '' : 'dark:hover:bg-gray-700 dark:hover:text-blue-400'}"
					on:click={() => {
						changeLanguage(lang.code);
					}}
				>
					<span> {lang.flag} </span>
					<span> {lang.title} </span>
				</button>
			{/each}
		</div>
	{/await}
</div>
