<script lang="ts">
    export let show = false;

    function submitForm(event: Event) {
        event.preventDefault();
        // Handle form submission logic here
        closeModal();
    }

    function closeModal() {
        show = false;
    }

    function handleOverlayClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            closeModal();
        }
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            closeModal();
        }
    }
</script>

<style>
    :root {
        --background-color: white;
        --text-color: #333;
        --input-background: #fff;
        --input-border: #ccc;
        --button-background: #1d4ed8;
        --button-hover-background: #1e40af;
        --button-text-color: white;
    }

    @media (prefers-color-scheme: dark) {
        :root {
            --background-color: #333;
            --text-color: #ddd;
            --input-background: #444;
            --input-border: #555;
            --button-background: #2563eb;
            --button-hover-background: #1d4ed8;
            --button-text-color: white;
        }
    }

    .modal-overlay {
        background-color: rgba(0, 0, 0, 0.5);
    }

    .form-container {
        background-color: var(--background-color);
        color: var(--text-color);
    }

    .form-input {
        background-color: var(--input-background);
        border-color: var(--input-border);
        color: var(--text-color);
    }

    .form-button {
        background-color: var(--button-background);
        color: var(--button-text-color);
    }

    .form-button:hover {
        background-color: var(--button-hover-background);
    }
</style>

{#if show}
<div class="fixed inset-0 flex items-center justify-center modal-overlay" on:click={handleOverlayClick} on:keydown={handleKeyDown} tabindex="0">
    <form class="form-container shadow-md rounded px-8 pt-6 pb-8 mb-4 grid grid-cols-2 gap-4" on:submit={submitForm}>
        <div class="col-span-1">
            <label class="block text-sm font-bold mb-2" for="lastname">
                Nom *
            </label>
            <input class="form-input shadow appearance-none border rounded w-full py-2 px-3 leading-tight focus:outline-none focus:shadow-outline" id="lastname" type="text" placeholder="Smith">
        </div>
        <div class="col-span-1">
            <label class="block text-sm font-bold mb-2" for="firstname">
                Prénom *
            </label>
            <input class="form-input shadow appearance-none border rounded w-full py-2 px-3 leading-tight focus:outline-none focus:shadow-outline" id="firstname" type="text" placeholder="John">
        </div>
        <div class="col-span-1">
            <label class="block text-sm font-bold mb-2" for="company">
              Société *
            </label>
            <input class="form-input shadow appearance-none border rounded w-full py-2 px-3 leading-tight focus:outline-none focus:shadow-outline" id="company" type="text" placeholder="John Smith & Co">
        </div>
        <div class="col-span-1">
            <label class="block text-sm font-bold mb-2" for="position">
              Poste *
            </label>
            <input class="form-input shadow appearance-none border rounded w-full py-2 px-3 leading-tight focus:outline-none focus:shadow-outline" id="position" type="text" placeholder="Responsable Marketing">
        </div>
        <div class="col-span-2">
            <label class="block text-sm font-bold mb-2" for="email">
              Email *
            </label>
            <input class="form-input shadow appearance-none border rounded w-full py-2 px-3 leading-tight focus:outline-none focus:shadow-outline" id="email" type="text" placeholder="johnsmith@jsco.com">
        </div>
        <div class="col-span-2">
            <label class="block text-sm font-bold mb-2" for="phone">
              Téléphone *
            </label>
            <input class="form-input shadow appearance-none border rounded w-full py-2 px-3 leading-tight focus:outline-none focus:shadow-outline" id="phone" type="text" placeholder="+33 1 02 03 04 05">
        </div>
        <div class="col-span-2">
            <button type="submit" class="form-button mt-4 w-full inline-flex justify-center py-3 px-4 border border-transparent shadow-sm text-sm font-medium rounded-3xl focus:outline-none focus:ring-2 focus:ring-offset-2">
                Submit
            </button>
        </div>
    </form>
</div>
{/if}