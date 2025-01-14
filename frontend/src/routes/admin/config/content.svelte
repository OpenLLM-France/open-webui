<script lang="ts">
    import { Card, Toggle, Button, Range, Label, Input, Modal } from "flowbite-svelte";
    import ConfigSaveToast from "$lib/admin_cmpnts/ConfigSaveToast.svelte";

    // Keep in mind these values are the MAXIMUM values for the range selectors, not the current values
    const max_nb_connections_range = 1000;
    const draft_time_limit_range = 60; // In minutes

    let confirmationModal = false;

    let initial_config = {
        max_nb_connections: 50,
        draft_time_limit: 5,
        enable_new_connections: true,
    };

    let editable_config = {
        max_nb_connections: 50,
        draft_time_limit: 5,
        enable_new_connections: true,
    };

    function check_changes(): void {
        if (JSON.stringify(initial_config) != JSON.stringify(editable_config)) { // I'll be honest, I don't like this
            changes = true;
        } else {
            changes = false;
        }
    }
    let changes = false;
    
</script>

<div class="p-4 w-full gap-4 h-screen overflow-y-auto">
    <div>
        <h5
            class="mb-2 text-2xl font-bold tracking-tight text-gray-900 dark:text-white"
        >
            Configuration settings
        </h5>
        <Card class="w-full max-w-none mb-4">
            <div>
                <Label>Maximum simultaneous users</Label>
                <div class="flex items-center gap-4">
                    <Range
                        min="0"
                        max={max_nb_connections_range}
                        bind:value={editable_config.max_nb_connections}
                        on:change={check_changes}
                    />
                    <Input
                        type="number"
                        bind:value={editable_config.max_nb_connections}
                        class="w-16"
                        on:change={check_changes}
                    />
                </div>
            </div>
            <div>
                <Label>Time limit in draft queue (in minutes)</Label>
                <div class="flex items-center gap-4">
                    <Range
                        min="0"
                        max={draft_time_limit_range}
                        bind:value={editable_config.draft_time_limit}
                        on:change={check_changes}
                    />
                    <Input
                        type="number"
                        bind:value={editable_config.draft_time_limit}
                        class="w-16"
                        on:change={check_changes}
                    />
                </div>
            </div>
        </Card>
    </div>

    <div>
        <h5
            class="mb-2 text-2xl font-bold tracking-tight text-gray-900 dark:text-white"
        >
            Panic settings
        </h5>
        <Card class="w-full max-w-none gap-4">
            <Toggle on:change={check_changes} bind:checked={editable_config.enable_new_connections}>Enable new connections to Lucie Chat</Toggle>
            <Button on:click={() => (confirmationModal = true)} >Kick all users</Button>

            <Modal bind:open={confirmationModal} size="xs">
                <div class="text-center">
                    <h5 class="text-lg font-bold">Are you sure you want to kick all users?</h5>
                    <div class="flex justify-center gap-4 mt-4">
                        <Button on:click={() => (confirmationModal = false)} color="alternative">Cancel</Button>
                        <Button on:click={() => (confirmationModal = false)} color="red">Confirm kick</Button>
                    </div>
                </div>
            </Modal>
        </Card>
    </div>
    <ConfigSaveToast show={changes}/>
</div>