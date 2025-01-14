<script lang="ts">
    import { page } from "$app/stores";
    import {
        Sidebar,
        SidebarGroup,
        SidebarItem,
        SidebarWrapper,
        DarkMode,
        Button,
    } from "flowbite-svelte";
    import { ChartPieSolid, CogSolid, HomeSolid, BugSolid } from "flowbite-svelte-icons";
    $: activeUrl = $page.url.pathname;

    let sidebarIconStyle =
        "w-6 h-6 text-gray-500 transition duration-75 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-white";
</script>

<Sidebar {activeUrl} class="h-screen overflow-hidden border-r dark:border-gray-700">
    <SidebarWrapper class="rounded-none p-4"> <!-- Add padding here -->
        <SidebarGroup class="min-h-screen ">
            <SidebarItem label="Dashboard" class="group" href="/admin">
                <svelte:fragment slot="icon">
                    <HomeSolid class={sidebarIconStyle} />
                </svelte:fragment>
            </SidebarItem>
            <SidebarItem
                label="Configuration"
                class="group"
                href="/admin/config"
            >
                <svelte:fragment slot="icon">
                    <CogSolid class={sidebarIconStyle} />
                </svelte:fragment>
            </SidebarItem>
            <SidebarItem
                label="Statistics"
                class="group"
                href="/admin/stats"
            >
                <svelte:fragment slot="icon">
                    <ChartPieSolid class={sidebarIconStyle} />
                </svelte:fragment>
            </SidebarItem>
            <DarkMode />
            <!-- Manually adjusting button to be identical to dark mode implementation -->
            <button class="text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none rounded-lg text-sm p-2.5">
                <a href="https://github.com/OpenLLM-France/FanLine/issues/new/choose"><BugSolid class="w-5 h-5 text-gray-500 dark:text-gray-400" /></a>
            </button>
        </SidebarGroup>
    </SidebarWrapper>
</Sidebar>


