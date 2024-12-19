<script lang="ts">
	import { termsOfUseAccepted } from '$lib/stores';
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n'); // Translations

	let termsScrolled = false;
	let popupRef: HTMLDivElement | null = null;

	// Function to check if the terms of use are fully scrolled
	const handleScroll = (event: Event) => {
		const element = event.target as HTMLDivElement;
		termsScrolled = element.scrollTop + element.clientHeight >= element.scrollHeight - 25;
	};

	// Stick focus within the popup
	const stickFocus = (event: KeyboardEvent) => {
		if (!popupRef) return;

		const focusableElements = popupRef.querySelectorAll<HTMLElement>(
			'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
		);
		const firstElement = focusableElements[0];
		const lastElement = focusableElements[focusableElements.length - 1];

		if (event.key === 'Tab') {
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

	onMount(() => {
		// Focus the popup container
		if (popupRef) {
			popupRef.focus();
		}

		// Prevent focus on other elements
		const handleFocus = (event: FocusEvent) => {
			if (popupRef && !popupRef.contains(event.target as Node)) {
				event.preventDefault();
				popupRef.focus();
			}
		};

		document.addEventListener('focusin', handleFocus);
		document.addEventListener('keydown', stickFocus);

		return () => {
			// Cleanup event listeners
			document.removeEventListener('focusin', handleFocus);
			document.removeEventListener('keydown', stickFocus);
		};
	});
</script>

{#if !$termsOfUseAccepted}
	<div class="h-screen w-screen absolute backdrop-blur-sm backdrop:disabled z-50 bg-white/30"></div>
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div
		class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1/2 h-2/3 p-12 pb-8 flex flex-col border shadow-xl rounded-3xl bg-white z-50"
		tabindex="0"
		bind:this={popupRef}
	>
		<div class="mb-8 text-3xl font-bold">
			{$i18n.t('Please accept the terms of use to keep chatting')}
		</div>

		<div
			id="terms"
			class="overflow-y-auto shadow-inner border py-2 px-4 text-gray-600"
			on:scroll={handleScroll}
		>
			Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus in nisl luctus, imperdiet mi
			in, porttitor risus. Nullam lacinia pharetra consequat. Suspendisse cursus turpis a nulla
			faucibus auctor. Sed tellus urna, accumsan vitae lacinia in, tristique vitae turpis.
			Pellentesque tortor nunc, mollis vitae congue id, varius at enim. Morbi vulputate est turpis,
			at viverra lorem faucibus eu. Fusce malesuada ac ipsum et porttitor. Interdum et malesuada
			fames ac ante ipsum primis in faucibus. Nullam dui leo, ullamcorper at augue non, porttitor
			dictum elit. Suspendisse dapibus consectetur ex, eget semper nisi tincidunt mollis. Lorem
			ipsum dolor sit amet, consectetur adipiscing elit. Suspendisse vel diam eu nibh posuere
			porttitor. Aliquam finibus ligula nulla. Nam eu faucibus magna. Duis quis placerat est. Morbi
			suscipit rhoncus nunc nec viverra. Quisque mauris eros, consequat vitae ante ut, dignissim
			congue turpis. Praesent tincidunt velit non dictum dignissim. Aenean turpis nunc, commodo et
			pretium luctus, congue sit amet ante. Donec faucibus, turpis eu feugiat gravida, risus risus
			facilisis velit, eget facilisis nulla odio eleifend magna. Aliquam id ipsum efficitur,
			hendrerit sapien et, feugiat purus. Integer justo neque, posuere id bibendum eget, posuere non
			dui. Sed malesuada lacinia justo. In pellentesque nisl id faucibus consectetur. Aliquam
			aliquam iaculis nisi id eleifend. Vestibulum placerat vel turpis ut malesuada. Phasellus
			pretium nibh ut nisi porta condimentum. Sed ac mi arcu. Ut varius quam tristique ultrices
			aliquet. Duis augue dolor, iaculis interdum pellentesque eu, tempus sed est. Mauris et
			faucibus lorem, et fringilla diam. Nam pharetra urna quam, nec rutrum nibh facilisis vel. Ut
			fringilla volutpat ultricies. Suspendisse iaculis, dui aliquet porttitor suscipit, neque
			tortor suscipit metus, ac ultrices ligula odio in justo. Cras egestas luctus vestibulum.
			Phasellus semper nisi ultricies dictum posuere. Cras semper metus nisi, eu vestibulum libero
			facilisis ut. Sed sem sapien, eleifend vitae semper et, tincidunt in ante. Maecenas non tortor
			at ligula finibus auctor. Proin ac erat libero. Ut sodales risus sit amet feugiat suscipit.
			Fusce venenatis purus sit amet volutpat dictum. Praesent non egestas erat. Maecenas fermentum,
			lectus nec accumsan malesuada, mi nulla vulputate nisl, quis sodales quam libero in ligula.
			Duis luctus lectus eu cursus luctus. Suspendisse in sapien eu sem dignissim molestie varius
			sit amet risus. Nulla in elit ante. Nunc vulputate, lacus ut varius consequat, magna lacus
			eleifend purus, eu finibus augue enim a elit. Quisque egestas est sit amet leo consectetur
			eleifend. Mauris vehicula at neque sagittis efficitur. Integer tincidunt ligula nec laoreet
			pretium. Nunc ac mi sem. Maecenas euismod ex sit amet nisi blandit, in lobortis nunc
			elementum. Maecenas ut ipsum tempor, aliquet lectus ac, pretium nisl. Aenean ac sem vel nulla
			pretium accumsan. Quisque posuere viverra tortor sed commodo. Etiam sit amet volutpat nisi.
			Cras sit amet tincidunt nisl. Pellentesque auctor congue ligula quis fermentum. Proin
			venenatis dolor tellus, sed rutrum ante maximus sed. Sed ac tortor sed orci hendrerit ornare
			eu sed diam. Mauris justo nulla, congue eu dictum non, cursus a lacus. Nam tempus urna non
			tempor bibendum. Proin pellentesque tellus vestibulum eros accumsan blandit. Vivamus dictum in
			massa vitae facilisis. Ut eu metus vitae ipsum mattis fermentum id ut quam. Vestibulum
			consequat nisi enim, sed luctus dolor suscipit sed. Pellentesque accumsan quam et mi
			ullamcorper, efficitur aliquam turpis laoreet. Nunc orci turpis, mollis et orci nec, laoreet
			finibus urna. Quisque erat eros, pretium tempus rhoncus nec, lacinia vitae diam. Nullam
			convallis sodales lacus. Vestibulum suscipit nisi id justo interdum ultricies. Nam sit amet
			nisi sit amet quam faucibus vehicula. Vestibulum sit amet leo nec sapien aliquam ullamcorper
			quis ac nunc. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac
			turpis egestas. Proin ac lacus egestas, fringilla tortor eu, dignissim mi. Proin eget nisi
			nulla. Aenean convallis nunc eu sapien tincidunt egestas. Duis massa tortor, iaculis eu
			iaculis id, pulvinar eget enim. Nulla sapien orci, semper in dui sed, vehicula rutrum orci.
			Quisque mattis lacus a finibus varius. Sed fermentum luctus augue, at sagittis leo
			pellentesque eget. Nullam euismod, quam sit amet sodales finibus, enim lacus euismod sapien,
			sed iaculis lacus felis vitae massa. Aliquam molestie lacus gravida, convallis metus eu,
			ullamcorper enim. Donec eu venenatis leo, quis feugiat magna. Quisque tempus justo in nisl
			consectetur, at tincidunt massa efficitur. Maecenas sed diam laoreet, pulvinar nibh a,
			elementum nisl. Mauris molestie purus nisi, ac posuere velit fermentum vel. Interdum et
			malesuada fames ac ante ipsum primis in faucibus. Praesent ut nisi velit. Praesent dictum
			vehicula luctus. Proin congue porttitor ornare. Donec ut mollis augue. Vestibulum pellentesque
			efficitur est, nec vehicula eros rhoncus sed. Nam eu mi scelerisque, hendrerit libero ac,
			vehicula ante. In volutpat pellentesque ultricies. Cras at elit vel orci sagittis facilisis
			sit amet a ligula. Nam dictum accumsan odio sit amet scelerisque. Maecenas a dignissim sem.
			Pellentesque auctor scelerisque nibh, et aliquam tellus aliquet eget. Nam vulputate nibh
			ornare nulla semper lobortis. Integer nec ligula velit. Duis elementum eros eget massa
			ultrices blandit. Aenean pretium facilisis tempus. Duis blandit, enim quis pellentesque
			gravida, dolor elit consectetur tortor, a tempor risus lacus non purus. Donec in ultricies
			tortor. Nullam sed rutrum purus, et aliquet dolor. In et semper massa, eu tristique est. Class
			aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Morbi
			vel molestie enim. Pellentesque interdum purus in lacus suscipit, suscipit porttitor diam
			auctor. Nunc ut blandit ante. Curabitur fermentum lectus eget felis mattis pellentesque.
			Integer gravida eleifend erat. In hac habitasse platea dictumst. Maecenas ac magna ut neque
			rutrum facilisis eu eget nisl. Vestibulum mollis, ipsum at viverra suscipit, neque elit
			sagittis eros, eu finibus arcu ante ut quam. Nunc ut ipsum eget arcu varius lobortis nec sit
			amet ligula. Aliquam malesuada tortor sit amet neque finibus, ut malesuada leo tincidunt.
			Maecenas tincidunt, leo tempor gravida lobortis, eros mauris interdum arcu, nec egestas leo
			massa quis nunc. Sed sed felis a ipsum semper porttitor. Maecenas blandit aliquet lacus, et
			lobortis leo volutpat sed. Integer cursus fermentum elit non consectetur. Curabitur egestas,
			lorem non lacinia tempus, sapien mi dignissim libero, vel dictum mauris nulla eget lectus.
			Vestibulum molestie dignissim nulla, eget hendrerit felis tincidunt non. Phasellus dictum ac
			lectus eu ultricies. Nulla hendrerit finibus dignissim. Vestibulum nec malesuada turpis.
			Aenean ac metus sem. Quisque sit amet lacinia massa, et sollicitudin turpis. Mauris sagittis
			at arcu sed mattis. Duis elementum, dui et finibus pulvinar, nisi erat sodales odio, nec
			sagittis elit odio at dolor. Cras placerat nibh at varius blandit. Vivamus semper lectus ac
			ligula scelerisque aliquam. In hac habitasse platea dictumst. Vestibulum in congue orci. Fusce
			vestibulum iaculis odio at iaculis. Aliquam aliquam non felis in faucibus. Class aptent taciti
			sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Suspendisse ultrices
			diam ut quam auctor, eget dapibus elit facilisis. Maecenas sit amet egestas risus, non
			interdum augue. Integer placerat mi nulla, id pharetra est condimentum eu. Proin quis auctor
			enim. Ut consectetur blandit dui, sit amet sollicitudin turpis fermentum quis. Integer
			tristique ante dui, ut malesuada magna facilisis sed. Praesent sit amet volutpat ligula. Duis
			rhoncus libero tortor, id commodo tortor dapibus in. Curabitur at dictum risus. Donec sed
			condimentum dui. Proin gravida felis eu commodo consequat. Donec at tempus elit. Sed
			scelerisque dignissim blandit. Nulla vestibulum dapibus eros, eget sollicitudin ante.
			Pellentesque at eleifend sem. Nunc accumsan ipsum nec neque tempus, id malesuada arcu
			condimentum. Morbi tellus ex, aliquam non euismod at, maximus non purus. Duis at viverra
			sapien, at egestas elit. Fusce commodo metus quis auctor tempus. Vivamus vitae viverra diam.
			Proin mollis ipsum vel purus scelerisque mollis. Curabitur ornare, sapien non ornare varius,
			orci massa pulvinar mauris, non feugiat magna libero at metus. Donec leo erat, gravida at
			dapibus at, efficitur non diam. Aenean ultricies elementum tincidunt. Aliquam erat volutpat.
			Aliquam facilisis accumsan blandit. Maecenas mollis turpis a velit pellentesque facilisis.
			Suspendisse potenti. Praesent non egestas neque. Integer ultrices faucibus lobortis. Cras sed
			porta enim, eu vulputate libero. Phasellus consequat nec dui interdum scelerisque. Interdum et
			malesuada fames ac ante ipsum primis in faucibus. Donec luctus nunc eu purus bibendum ornare.
			Phasellus malesuada erat luctus quam venenatis, at scelerisque lectus maximus. Phasellus sed
			nulla nunc. Nullam rutrum neque et ligula facilisis dapibus. Proin commodo nisi eget ultricies
			bibendum. Morbi pharetra elit sed ante molestie, ut finibus neque varius.
		</div>

		<div class="mt-8 self-end flex space-x-6">
			<button
				class="py-3 px-6 rounded-full text-gray-500 hover:text-red-800 disabled:text-gray-500 disabled:cursor-not-allowed"
				disabled={!termsScrolled}
			>
				{$i18n.t('Decline')}
			</button>
			<button
				class="py-3 px-6 bg-black text-white rounded-full hover:bg-gray-800 disabled:bg-gray-500 disabled:cursor-not-allowed"
				disabled={!termsScrolled}
				on:click={() => {
					$termsOfUseAccepted = true;
				}}
			>
				{$i18n.t('Accept')}
			</button>
		</div>
	</div>
{/if}
