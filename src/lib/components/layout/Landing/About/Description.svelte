<script>
	// Import translation utility and global store
	import i18n from '$lib/i18n';
	import { WEBUI_NAME } from '$lib/stores';
</script>

<div
	class=" bg-gradient-to-r from-blue-50 from-40% via-white to-60% to-red-50"
>
	<div class="grid grid-cols-2 gap-48">
		<!-- What is LUCIE ? -->
		<div>
			<div class="text-2xl xl:text-3xl 2xl:text-4xl mb-4 xl:mb-8">
				{$i18n.t('What is {{WEBUI_NAME}} ?', { WEBUI_NAME: $WEBUI_NAME })}
			</div>
			<div class="flex flex-col space-y-4 text-justify text-sm xl:text-base 2xl:text-lg">
				<span>
					LUCIE est, encore à ce stade, un projet de recherche académique, issu de la communauté
					OpenLLM France initiée par Michel-Marie MAUDET, Directeur Général de LINAGORA, le pionier
					français de l’Open Source le 16 juin 2023.
				</span>

				<span>
					A l’origine, LUCIE a été développée sur fonds propres par LINAGORA puis, dans un 2ème
					temps, a pu bénéficier d’un financement spécifique issu d’un Appel à Projet «&nbsp;Communs
					Numériques&nbsp;» dans le cadre du programme d’investissements d’avenir France 2030
					attribué à un consortium public/privé comptant, en plus de LINAGORA, le CNRS, l’Ecole
					Politechnique, l’Opsci, l’association Classcode et Talkr.
				</span>
			</div>
		</div>
		<div>
			<div class="text-2xl xl:text-3xl 2xl:text-4xl mb-4 xl:mb-8">
				{$i18n.t('Origins of the name of {{WEBUI_NAME}} model', { WEBUI_NAME: '' })}
			</div>
			<div class="flex flex-col space-y-4 text-justify text-sm xl:text-base 2xl:text-lg">
				<span>
					{$i18n.t(
						'{{WEBUI_NAME}} is our truly Open Source artificial intelligence, developed in collaboration with the OpenLLM-France community and supported by the French General Secretariat for Investment.',
						{ WEBUI_NAME: $WEBUI_NAME }
					)}
				</span>
				<span>
					{$i18n.t('The name {{WEBUI_NAME}} carries a dual symbolism:', {
						WEBUI_NAME: $WEBUI_NAME
					})}
				</span>
				<ol class="list-decimal list-inside space-y-2">
					<li>
						{$i18n.t(
							'It echoes "Lucy", the common ancestor of all humanity, representing universal origins and connection.'
						)}
					</li>
					<li>
						{$i18n.t(
							'It also refers to the main character of the film "Lucy" by Luc Besson, who masters all human knowledge.'
						)}
					</li>
				</ol>
				<span>
					{$i18n.t(
						'Her face is inspired by Marianne, the French Republic\'s emblem, while also reminiscent of Scarlett Johansson, the heroine of the film "Lucy". Draped in a tricolor shawl, {{WEBUI_NAME}} embodies sovereignty and French values.',
						{ WEBUI_NAME: $WEBUI_NAME }
					)}
				</span>
			</div>
		</div>
	</div>
</div>
