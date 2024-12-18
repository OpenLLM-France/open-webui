<script>
	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { ldapUserSignIn, getSessionUser, userSignIn, userSignUp } from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket, mobile } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let name = '';
	let email = '';
	let password = '';

	let ldapUsername = '';

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}

			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());
			goto('/');
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(error);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(error);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(error);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (mode === 'ldap') {
			await ldapSignInHandler();
		} else if (mode === 'signin') {
			await signInHandler();
		} else {
			await signUpHandler();
		}
	};

	const checkOauthCallback = async () => {
		if (!$page.url.hash) {
			return;
		}
		const hash = $page.url.hash.substring(1);
		if (!hash) {
			return;
		}
		const params = new URLSearchParams(hash);
		const token = params.get('token');
		if (!token) {
			return;
		}
		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(error);
			return null;
		});
		if (!sessionUser) {
			return;
		}
		localStorage.token = token;
		await setSessionUser(sessionUser);
	};

	let onboarding = false;

	onMount(async () => {
		if ($user !== undefined) {
			await goto('/');
		}
		await checkOauthCallback();

		loaded = true;
		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
			if (onboarding) mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<!-- 
<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>
-->

<div
	class="w-screen h-screen px-12 flex flex-col items-center bg-[url('/assets/design/abstract-circle.png')] bg-no-repeat bg-contain overflow-y-auto
	md:flex-row-reverse md:overflow-hidden"
>
	{#if loaded}
		<!-- Linagora AI logo-->
		<img
			crossorigin="anonymous"
			src="/assets/logos/linagora-ai.png"
			class="h-12 my-6 md:hidden"
			alt="Linagora AI logo"
		/>
		<!-- Lucie Illustration -->
		<img
			crossorigin="anonymous"
			src="/assets/images/lucie.png"
			class="h-80 -z-10 md:hidden"
			alt="Lucie illustration"
		/>
		<div class="flex flex-col items-center md:mr-4 md:h-screen md:justify-center">
			<img
				crossorigin="anonymous"
				src="/assets/logos/linagora-ai.png"
				class="my-6 h-12 max-md:hidden"
				alt="Linagora AI logo"
			/>
			<!-- Sign in/up form -->
			{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
				<div class="py-6">
					<div
						class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-semibold dark:text-gray-200"
					>
						<div>
							{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
						</div>

						<div>
							<Spinner />
						</div>
					</div>
				</div>
			{:else}
				<div class="py-6">
					<form
						class="flex flex-col justify-center"
						on:submit={(e) => {
							e.preventDefault();
							submitHandler();
						}}
					>
						<div class="mb-1">
							<div class="text-xl md:text-2xl font-medium text-center">
								{#if $config?.onboarding ?? false}
									{$i18n.t(`Get started with {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
								{:else if mode === 'ldap'}
									{$i18n.t(`Sign in to {{WEBUI_NAME}} with LDAP`, { WEBUI_NAME: $WEBUI_NAME })}
								{:else if mode === 'signin'}
									{$i18n.t(`Sign in to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
								{:else}
									{$i18n.t(`Sign up to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
								{/if}
							</div>

							{#if $config?.onboarding ?? false}
								<div class="mt-1 text-xs md:text-sm text-gray-500 text-center">
									ⓘ {$WEBUI_NAME}
									{$i18n.t(
										'does not make any external connections, and your data stays securely on your locally hosted server.'
									)}
								</div>
							{/if}
						</div>

						{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
							<div class="flex flex-col mt-4">
								{#if mode === 'signup'}
									<div class="mb-4">
										<div class=" text-sm font-medium text-left mb-1">{$i18n.t('Name')}</div>
										<input
											bind:value={name}
											type="text"
											class="my-0.5 w-full text-sm outline-none bg-transparent"
											autocomplete="name"
											placeholder={$i18n.t('Enter Your Full Name')}
											required
										/>
									</div>
								{/if}

								{#if mode === 'ldap'}
									<div class="mb-4">
										<div class=" text-sm font-medium text-left mb-1">{$i18n.t('Username')}</div>
										<input
											bind:value={ldapUsername}
											type="text"
											class="my-0.5 w-full text-sm outline-none bg-transparent"
											autocomplete="username"
											name="username"
											placeholder={$i18n.t('Enter Your Username')}
											required
										/>
									</div>
								{:else}
									<div class="mb-4">
										<div class=" text-sm font-medium text-left mb-1">{$i18n.t('Email')}</div>
										<input
											bind:value={email}
											type="email"
											class="my-0.5 w-full text-sm outline-none bg-transparent"
											autocomplete="email"
											name="email"
											placeholder={$i18n.t('Enter Your Email')}
											required
										/>
									</div>
								{/if}

								<div class="mb-4">
									<div class=" text-sm font-medium text-left mb-1">{$i18n.t('Password')}</div>

									<input
										bind:value={password}
										type="password"
										class="my-0.5 w-full text-sm outline-none bg-transparent"
										placeholder={$i18n.t('Enter Your Password')}
										autocomplete="current-password"
										name="current-password"
										required
									/>
								</div>
							</div>
						{/if}
						<div class="mt-4">
							{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
								{#if mode === 'ldap'}
									<button
										class="bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
										type="submit"
									>
										{$i18n.t('Authenticate')}
									</button>
								{:else}
									<button
										class="bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
										type="submit"
									>
										{mode === 'signin'
											? $i18n.t('Sign in')
											: ($config?.onboarding ?? false)
												? $i18n.t('Create Admin Account')
												: $i18n.t('Create Account')}
									</button>

									{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
										<div class=" mt-4 text-sm text-center">
											{mode === 'signin'
												? $i18n.t("Don't have an account?")
												: $i18n.t('Already have an account?')}

											<button
												class=" font-medium underline"
												type="button"
												on:click={() => {
													if (mode === 'signin') {
														mode = 'signup';
													} else {
														mode = 'signin';
													}
												}}
											>
												{mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
											</button>
										</div>
									{/if}
								{/if}
							{/if}
						</div>
					</form>

					{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
						<div class="flex items-center justify-center w-full">
							<hr class="w-full h-px my-6 border-0 dark:bg-gray-100/10 bg-gray-700/10" />
							{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
								<span
									class="px-3 text-sm font-medium text-gray-900 dark:text-white bg-transparent text-nowrap"
								>
									{$i18n.t('or')}
								</span>
							{/if}

							<hr class="w-full h-px my-4 border-0 dark:bg-gray-100/10 bg-gray-700/10" />
						</div>
						<div class="flex flex-col space-y-2">
							{#if $config?.oauth?.providers?.google}
								<button
									class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
									on:click={() => {
										window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
									}}
								>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" class="size-6 mr-3">
										<path
											fill="#EA4335"
											d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
										/><path
											fill="#4285F4"
											d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
										/><path
											fill="#FBBC05"
											d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
										/><path
											fill="#34A853"
											d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
										/><path fill="none" d="M0 0h48v48H0z" />
									</svg>
									<span>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span>
								</button>
							{/if}
							{#if $config?.oauth?.providers?.microsoft}
								<button
									class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
									on:click={() => {
										window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
									}}
								>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 21 21" class="size-6 mr-3">
										<rect x="1" y="1" width="9" height="9" fill="#f25022" /><rect
											x="1"
											y="11"
											width="9"
											height="9"
											fill="#00a4ef"
										/><rect x="11" y="1" width="9" height="9" fill="#7fba00" /><rect
											x="11"
											y="11"
											width="9"
											height="9"
											fill="#ffb900"
										/>
									</svg>
									<span>{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}</span>
								</button>
							{/if}
							{#if $config?.oauth?.providers?.oidc}
								<button
									class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
									on:click={() => {
										window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="size-6 mr-3"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
										/>
									</svg>

									<span
										>{$i18n.t('Continue with {{provider}}', {
											provider: $config?.oauth?.providers?.oidc ?? 'SSO'
										})}</span
									>
								</button>
							{/if}
						</div>
					{/if}

					{#if ($config?.features.enable_ldap && $config?.features.enable_login_form)}
						<div class="mt-2">
							<button
								class="flex justify-center items-center text-xs w-full text-center underline"
								type="button"
								on:click={() => {
									if (mode === 'ldap') mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
									else mode = 'ldap';
								}}
							>
								<span
									>{mode === 'ldap'
										? $i18n.t('Continue with Email')
										: $i18n.t('Continue with LDAP')}</span
								>
							</button>
						</div>
					{/if}
				</div>
			{/if}

			<div class="my-4 flex items-center space-x-4">
				<img
					crossorigin="anonymous"
					src="/assets/logos/openllm-france.png"
					class="h-24"
					alt="OpenLLM France logo"
				/>
				<img
					crossorigin="anonymous"
					src="/assets/openllm-qrcode.png"
					class="h-24"
					alt="OpenLLM QR Code"
				/>
			</div>
		</div>
		<div
			class="mt-6 md:pt-20 flex flex-col items-center w-full md:items-start md:h-screen md:relative"
		>
			<img
				crossorigin="anonymous"
				src="/assets/logos/lucie.png"
				class="h-12 md:mt-6 md:h-20 md:-z-10"
				alt="Lucie logo"
			/>
			<img
				crossorigin="anonymous"
				src="/assets/images/lucie.png"
				class="absolute right-16 h-4/5 max-md:hidden"
				alt="Lucie illustration"
			/>
			<div class="mt-6 text-center md:text-left md:w-1/2">
				<div class="text-xl md:text-5xl font-semibold leading-snug tracking-wide">
					{$i18n.t('The first generative AI really Open Source')}
				</div>
				<div
					class="mt-1 md:mt-3 text-sm md:text-xl font-semibold leading-relaxed tracking-wide text-gray-500"
				>
					{$i18n.t('with 100% transparent training data')}
				</div>
			</div>
			<div class="grow max-md:hidden" />
			<img
				crossorigin="anonymous"
				src="/assets/logos/france-2030-laureat.png"
				class="h-28 my-6 md:h-32"
				alt="France 2030 Lauréat logo"
			/>
			<div class="mb-12 grid grid-cols-2 items-center justify-center gap-8 md:flex">
				<!-- Logos -->
				<img
					crossorigin="anonymous"
					src="/assets/logos/opsci.png"
					class="h-12 md:h-16 mx-auto"
					alt="OPSCI logo"
				/>
				<img
					crossorigin="anonymous"
					src="/assets/logos/talkr-ai.png"
					class="h-12 md:h-16 mx-auto"
					alt="Talkr.ai logo"
				/>
				<img
					crossorigin="anonymous"
					src="/assets/logos/class-code.png"
					class="w-24 md:w-28 mx-auto"
					alt="Class'Code logo"
				/>
				<img
					crossorigin="anonymous"
					src="/assets/logos/cea.png"
					class="h-12 md:h-16 mx-auto"
					alt="CEA logo"
				/>
				<img
					crossorigin="anonymous"
					src="/assets/logos/cnrs.png"
					class="h-12 md:h-16 mx-auto"
					alt="CNRS logo"
				/>
				<img
					crossorigin="anonymous"
					src="/assets/logos/loria.png"
					class="h-12 md:h-16 mx-auto"
					alt="Loria logo"
				/>
				<img
					crossorigin="anonymous"
					src="/assets/logos/lix.png"
					class="h-12 md:h-16 mx-auto"
					alt="LIX logo"
				/>
				<img
					crossorigin="anonymous"
					src="/assets/logos/sorbonne.png"
					class="w-28 md:w-32 mx-auto"
					alt="Sorbonne logo"
				/>
			</div>
		</div>
	{/if}
</div>
