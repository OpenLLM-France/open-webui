<script lang="ts">
    import { Card } from "flowbite-svelte";
    import { fly } from "svelte/transition";
    export let show = true;
    export let message;

    if (!message) {
        show = false;
    }
</script>

<style>
    .toast-container {
        display: flex;
        justify-content: center;
        align-items: center;
    }
</style>

{#if show}
    <div class="absolute bottom-4 right-4 toast-container">
        <div in:fly={{ y: 100, duration: 500 }} out:fly={{ y: 100, duration: 500 }}>
            <Card color="red">{message}</Card>
        </div>
    </div>
{/if}
