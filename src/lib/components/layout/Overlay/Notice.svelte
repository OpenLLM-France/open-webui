<script lang="ts">
	// Imports
	import { showNotice } from '$lib/stores';
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';

	const i18n: Writable<any> = getContext('i18n');

	let noticePopupRef: HTMLDivElement | null = null; // Represents the notice popup element

	/**
	 * Close the notice popup
	 */
	const closeNotice = () => {
		$showNotice = false;
	};

	/**
	 * Close the notice popup if a click is performed outside the popup, or on the 'I understand' and close buttons.
	 * @param event represents the mouseEvent
	 */
	const handleOverlayClick = (event: MouseEvent) => {
		if (event.target === event.currentTarget) {
			closeNotice();
		}
	};

	/**
	 * Handles key down events :
	 * Escape | Enter -> close notice
	 * Tab -> prevent focus on other page elements
	 */
	const handleKeyDown = (event: KeyboardEvent) => {
		if (!noticePopupRef) return;
		if (event.key === 'Escape' || event.key === 'Enter') {
			closeNotice();
			return;
		} else if (event.key === 'Tab') {
			const focusableElements = noticePopupRef.querySelectorAll<HTMLElement>(
				'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
			);
			const firstElement = focusableElements[0];
			const lastElement = focusableElements[focusableElements.length - 1];
			if (event.shiftKey && document.activeElement === firstElement) {
				// Shift + Tab pressed on the first element
				lastElement.focus();
				event.preventDefault();
			} else if (!event.shiftKey && document.activeElement === lastElement) {
				// Tab pressed on the last element
				firstElement.focus();
				event.preventDefault();
			}
		}
	};

	/**
	 * Running when the component is mounted to the DOM
	 */
	onMount(() => {
		// Focus the popup container
		if (noticePopupRef) {
			noticePopupRef.focus();
		}

		// Listen to events
		document.addEventListener('keydown', handleKeyDown);

		// Clean up event listeners when the component is unmounted
		return () => {
			document.removeEventListener('keydown', handleKeyDown);
		};
	});
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<!-- svelte-ignore a11y-click-events-have-key-events -->
<div
	class="absolute h-full w-full flex items-center justify-center backdrop-brightness-75 backdrop-blur-sm z-50
		selection:bg-blue-500/50"
	on:click={handleOverlayClick}
>
	<!-- Close button -->
	<button
		class="absolute top-5 right-5 text-white font-medium text-2xl cursor-pointer transition-all
			hover:text-gray-200
			max-md:hidden
			lg:right-6"
		on:click={handleOverlayClick}
	>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			viewBox="0 0 20 20"
			fill="currentColor"
			class="w-6 h-6"
			on:click={handleOverlayClick}
		>
			<path
				d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
			/>
		</svg>
	</button>

	<div
		class="w-11/12 h-[95vh] p-6 flex flex-col space-y-4 overflow-y-scroll rounded
			bg-white/90 backdrop-blur-md shadow-md text-gray-700 text-sm text-justify
			md:h-[80vh] md:w-4/5 md:p-10 md:space-y-6 md:text-base
			2xl:h-fit 2xl:w-2/3"
		bind:this={noticePopupRef}
	>
		<!-- Notice text -->
		<span class="text-xl font-medium md:text-2xl"> {$i18n.t('Notice')} </span>
		<div class="overflow-y-scroll space-y-4">
			<div>
				{$i18n.t(
					'Lucie is a large generative language model (LLM), which means that from an input text or “prompt”, it generates a response related to that input. LLMs have to go through many training phases before they can respond appropriately and accurately to various prompts, and Lucie is at a very early stage in her training, having received just one round of what is known as instructional refinement. This training, although light, enables Lucie to follow basic instructions, such as answering a question or summarizing a text. Her answers may not yet be reliable, but without this additional training, Lucie, given an instruction, would only be able to generate strings of words semantically related to that query. Her answers would not have the correct form.'
				)}
			</div>
			<div>
				{$i18n.t(
					'To move on to the next stages of training, we need to collect large amounts of data from interactions with human users. In particular, we need to know whether an answer provided by Lucie is right, wrong or preferable to another. If we get enough high-quality data of this kind, we can use it to train Lucie to align her responses with the preferences of human users.'
				)}
			</div>
			<div>
				{$i18n.t(
					"That's why we've created this platform: so that users can give us their feedback and help us improve Lucie's performance. As Lucie is trained on equal amounts of French and English (around 33% for each language), we welcome interactions in both languages, but are particularly interested in collecting data in French, as it is much more difficult to obtain than in English ."
				)}
			</div>
			<div>
				{$i18n.t(
					'Bear in mind when interacting with the model that it is not, and never will be, a French ChatGPT. The Lucie model is hundreds of times smaller than the models behind the ChatGPT platform; converting it into a general AI assistant of this type is simply impossible. Our interest is in creating a model to help generate texts in French and English, and to perform tasks for which basic language models perform well: summarizing documents, answering general knowledge questions (bearing in mind that it has only seen data up to 2023), answering questions based on input text, writing stories, and so on. It is not designed as an assistant for mathematics or coding, nor is it capable of providing ethical advice.'
				)}
			</div>
		</div>

		<!-- 'I understand' button -->
		<div class="flex justify-end">
			<button
				class="px-6 py-3 rounded-full bg-blue-500 hover:bg-blue-600 text-white"
				on:click={handleOverlayClick}
			>
				{$i18n.t('I understand')}
			</button>
		</div>
	</div>
</div>
