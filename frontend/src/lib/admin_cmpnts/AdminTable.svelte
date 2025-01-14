<script lang="ts">
    import {
        Table,
        TableBody,
        TableBodyCell,
        TableBodyRow,
        TableHead,
        TableHeadCell,
    } from "flowbite-svelte";
    import { TrashBinSolid } from "flowbite-svelte-icons";
    import { Button } from "flowbite-svelte";
    import { ArrowUpRightFromSquareSolid } from "flowbite-svelte-icons";
    import { leaveQueue } from "$lib/queue";
    import type { QueueStatus } from "$lib/types";

    export let columns;
    export let data;

    function handleDelete(row: QueueStatus) {
        // Implement your delete logic here
        console.log("Delete row:", row);
        leaveQueue(row)
            .then((data) => {
                console.log(data);
            })
            .catch((err) => {
                console.error(err.message);
            });

    }
</script>

{#if data && data.length > 0}
    <div class="border border-gray-200 dark:border-gray-700 rounded-lg">
        <Table shadow>
            <TableHead>
                {#each columns as column}
                    <TableHeadCell>{column.label}</TableHeadCell>
                {/each}
                <TableHeadCell>Actions</TableHeadCell>
            </TableHead>
            <TableBody tableBodyClass="divide-y">
                {#each data as row}
                    <TableBodyRow>
                        {#each columns as column}
                            <TableBodyCell>{row[column.key]}</TableBodyCell>
                        {/each}
                        <TableBodyCell>
                            <!-- Manually adjusting button to be identical to sidebar implementation -->
                            <button
                                class="text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none rounded-lg text-sm p-2.5"
                                on:click={() => handleDelete(row)}
                                ><TrashBinSolid
                                    class="w-5 h-5 text-gray-500 dark:text-gray-400"
                                />
                            </button>
                            <button
                                class="text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none rounded-lg text-sm p-2.5"
                                on:click={() => handlecheckout(row)}
                                ><ArrowUpRightFromSquareSolid
                                    class="w-5 h-5 text-gray-500 dark:text-gray-400"
                                />
                            </button>
                        </TableBodyCell>
                    </TableBodyRow>
                {/each}
            </TableBody>
        </Table>
    </div>
{/if}
