<script>
	// Import translation utility and global store
	import i18n from '$lib/i18n';
	import { WEBUI_NAME } from '$lib/stores';

	// Import components
	import {
		Timeline,
		TimelineItem,
		TimelineSeparator,
		TimelineDot,
		TimelineConnector,
		TimelineContent,
		TimelineOppositeContent
	} from 'svelte-vertical-timeline';
</script>

<!-- Timeline -->
<div class="max-xl:px-8 py-12 xl:py-24 flex flex-col items-center text-center bg-fixed bg-gradient-to-br from-blue-50 from-40% via-white to-60% to-red-50">
	<div class="text-3xl mb-8">
		{$i18n.t('Future of {{WEBUI_NAME}} in 2025', { WEBUI_NAME: $WEBUI_NAME })}
	</div>
	<div class="xl:px-[25vw] 2xl:px-[33vw] mb-8 xl:mb-16">
		{$i18n.t(
			"The journey of {{WEBUI_NAME}} is far from over. Our 2025 roadmap outlines ambitious milestones to enhance capabilities and expand the model's applications:",
			{ WEBUI_NAME: $WEBUI_NAME }
		)}
	</div>
	<div class="xl:px-[25vw] md:-translate-x-32 lg:-translate-x-48 xl:-translate-x-0">
		<Timeline>
			<TimelineItem>
				<TimelineOppositeContent slot="opposite-content">
					<span class="font-bold text-base xl:text-xl">Q1</span>
				</TimelineOppositeContent>
				<TimelineSeparator>
					<TimelineDot style={'background-color: transparent !important;'} />
					<TimelineConnector />
				</TimelineSeparator>
				<TimelineContent>
					<div class="flex flex-col max-md:w-52 xl:w-96 space-y-2 pb-12">
						<span class="text-lg xl:text-2xl">
							{$i18n.t('Enhanced fine-tuning and better toolkit for AI makers')}
						</span>
						<span class="text-sm">
							{$i18n.t(
								"We will refine {{WEBUI_NAME}}'s instruction-following capabilities (fine-instruct), introduce function calling for better integration with external systems, and release at least one model with fewer than 3 billion parameters to ensure accessibility for resource-constrained environments.",
								{ WEBUI_NAME: $WEBUI_NAME }
							)}
						</span>
					</div>
				</TimelineContent>
			</TimelineItem>
			<TimelineItem>
				<TimelineOppositeContent slot="opposite-content">
					<span class="font-bold text-base xl:text-xl">Q2</span>
				</TimelineOppositeContent>
				<TimelineSeparator>
					<TimelineDot />
					<TimelineConnector />
				</TimelineSeparator>
				<TimelineContent>
					<div class="flex flex-col max-md:w-52 xl:w-96 space-y-2 pb-12">
						<span class="text-lg xl:text-2xl">
							{$i18n.t('Advanced Retrieval-Augmented Generation (RAG)')}
						</span>
						<span class="text-sm">
							{$i18n.t(
								'{{WEBUI_NAME}} will gain an advanced RAG function, enabling it to leverage external knowledge bases for more accurate and context-aware responses.',
								{ WEBUI_NAME: $WEBUI_NAME }
							)}
						</span>
					</div>
				</TimelineContent>
			</TimelineItem>
			<TimelineItem>
				<TimelineOppositeContent slot="opposite-content">
					<span class="font-bold text-base xl:text-xl">Q3</span>
				</TimelineOppositeContent>
				<TimelineSeparator>
					<TimelineDot />
					<TimelineConnector />
				</TimelineSeparator>
				<TimelineContent>
					<div class="flex flex-col max-md:w-52 xl:w-96 space-y-2 pb-12">
						<span class="text-lg xl:text-2xl">
							{$i18n.t('Multimodal Version for {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
						</span>
						<span class="text-sm">
							{$i18n.t(
								"We will extend {{WEBUI_NAME}}'s capabilities into multimodal AI, with a focus on voice processing in French, opening new possibilities for applications in education, accessibility, and beyond.",
								{ WEBUI_NAME: $WEBUI_NAME }
							)}
						</span>
					</div>
				</TimelineContent>
			</TimelineItem>
			<TimelineItem>
				<TimelineOppositeContent slot="opposite-content">
					<span class="font-bold text-base xl:text-xl">Q4</span>
				</TimelineOppositeContent>
				<TimelineSeparator>
					<TimelineDot />
					<TimelineConnector />
				</TimelineSeparator>
				<TimelineContent>
					<div class="flex flex-col max-md:w-52 xl:w-96 space-y-2">
						<span class="text-lg xl:text-2xl"> {$i18n.t('Agentic AI Framework')} </span>
						<span class="text-sm">
							{$i18n.t(
								'{{WEBUI_NAME}} will evolve into a robust agentic AI framework, harnessing its capabilities to power autonomous systems and lay the foundation for Large Action Models (LAM) all while maintaining transparency, trust, and ethical safeguards.',
								{ WEBUI_NAME: $WEBUI_NAME }
							)}
						</span>
					</div>
				</TimelineContent>
			</TimelineItem>
		</Timeline>
		<!-- Styles for the timeline -->
		<style>
			.timeline {
				z-index: 0 !important;
				position: relative !important;
			}
			.timeline-dot {
				background-color: #4e4e4e !important;
				width: 20px !important;
				height: 20px !important;
				margin-bottom: 0px !important;
				margin-top: 0px !important;
				border: #4e4e4e solid 3px !important;
			}
			.timeline-connector {
				width: 3px !important;
				background-color: #4e4e4e !important;
			}
			.timeline-content,
			.timeline-opposite-content {
				margin-bottom: 0px !important;
				margin-top: 0px !important;
				transform: translateY(-7px);
			}
			@media not all and (min-width: 1024px) {
				.timeline-opposite-content {
					width: 28px;
					transform: translateY(-3px);
				}
				.timeline-content {
					transform: translateY(-5px);
				}
			}
		</style>
	</div>
</div>
