<script lang="ts">
    import SvelteTable from "svelte-table";
    import { Heart, Trash, Check } from "svelte-iconoir";
    import { Alert } from "flowbite-svelte";

    import {joinQueue, leaveQueue, confirmConnection, getMetrics} from "$lib/queue";
    import type { UserRequest } from "$lib/types";

    /**
     * Represents the simulated user's data in the queue.
     * @remarks
     * This is a temporary solution to be finalized or replaced by QueueStatus in types.ts
     *
     * @param id - The user's unique identifier.
     * @param status - The user's current status in the queue. waiting, draft, connected, or disconnected.
     * @param position - The user's position in the queue.
     * @param timeSinceJoin - The time in seconds since the user joined the queue.
     * @param draftTimer - The time in seconds since the user entered the draft.
     * @param sessionTimer - The time in seconds since the user entered the session.
     *
     */
    interface UserQueueStats {
        id: string;
        status: string;
        position: number;
        timeSinceJoin: number;
        draftTimer: number;
        sessionTimer: number;
    }

    let users: UserQueueStats[] = [];

    // Svelte-table columns
    const columns = [
        {
            title: "ID",
            key: "id",
            value: (v: UserQueueStats) => v.id,
            class: "px-4 py-2",
        },
        {
            title: "Status",
            key: "status",
            value: (v: UserQueueStats) => v.status,
            class: "px-4 py-2",
        },
        {
            title: "Position",
            key: "position",
            value: (v: UserQueueStats) => v.position,
            class: "px-4 py-2",
        },
        {
            title: "Time since join",
            key: "timeSinceJoin",
            value: (v: UserQueueStats) => v.timeSinceJoin,
            class: "px-4 py-2",
        },
        {
            title: "Draft timer",
            key: "draftTimer",
            value: (v: UserQueueStats) => v.draftTimer,
            class: "px-4 py-2",
        },
        {
            title: "Session timer",
            key: "sessionTimer",
            value: (v: UserQueueStats) => v.sessionTimer,
            class: "px-4 py-2",
        },
        {
            title: "Heartbeat",
            key: "heartbeat",
            renderComponent: Heart,
            class: "px-4 py-2",
        },
        {
            title: "Leave",
            key: "leave",
            renderComponent: Trash,
            class: "px-4 py-2",
        },
        {
            title: "Confirm",
            key: "confirm",
            renderComponent: Check,
            class: "px-4 py-2",
        },
    ];

    // Storing the last response from the server
    let lastResponse = "";

    /**
     * Generates a random user with default data.
     *
     * @returns A UserRequest object with the generated user's random user_id.
     * @remarks Also adds the user to the queue list. (Which should not be handled here)
     */
    function generateRandomUser() {
        let new_user_request: UserRequest = {
            user_id: Math.random().toString(36).substring(2, 9),
        };

        // Temporary solution to test table. This functionnality is supposed to be handled through an endpoint.
        let new_user: UserQueueStats = {
            id: new_user_request.user_id,
            status: "waiting",
            position: users.length + 1,
            timeSinceJoin: 0,
            draftTimer: 0,
            sessionTimer: 0,
        };

        users = [...users, new_user];
        return new_user_request;
    }

    /**
     * Adds a randomly generated user to the queue.
     */
    function handleAddUserToQueue() {
        let user = generateRandomUser();
        console.log("Adding user to queue");
        joinQueue(user)
            .then((data) => {
                console.log(data);
                lastResponse = JSON.stringify(data);
            })
            .catch((err) => {
                console.error(err.message);
                lastResponse = JSON.stringify(err.message);
            });
    }

    /**
     * Gets the global queue metrics from the server.
     * - active_users
     * - waiting_users
     * - total_slots
     */
    function handleGetMetrics() {
        console.log("Getting metrics");
        getMetrics()
            .then((data) => {
                console.log(data);
                lastResponse = JSON.stringify(data);
            })
            .catch((err) => {
                console.error(err.message);
                lastResponse = JSON.stringify(err.message);
            });
    }

    /**
     * Handles the click event on the table cells.
     *
     * @param e - The CustomEvent object containing the cell's details.
     */
    function handleClick(e: CustomEvent) {
        let detail = e.detail;

        if (detail.key == "heartbeat") {
            handleHeartbeat(detail.row);
        } else if (detail.key == "leave") {
            handleLeaveQueue(detail.row);
        } else if (detail.key == "confirm") {
            handleConfirmConnection(detail.row);
        }
        console.log(e);
    }

    /**
     * Handles the heartbeat event for a user. (Does nothing for now)
     * @param row - The user's data.
     */
    function handleHeartbeat(row: UserQueueStats) {
        console.log("Heartbeat for user", row.id);
    }

    /**
     * Requests the removal of a user from the queue from the server.
     * @param row - The user's data.
     */
    function handleLeaveQueue(row: UserQueueStats) {
        console.log("Leaving queue for user", row.id);
        let cur_user: UserRequest = {
            user_id: row.id,
        };
        leaveQueue(cur_user)
            .then((data) => {
                console.log(data);
                lastResponse = JSON.stringify(data);
            })
            .catch((err) => {
                console.error(err.message);
                lastResponse = JSON.stringify(err.message);
            });
    }

    /**
     * Requests the confirmation of a connection for a user from the server.
     * @param row - The user's data.
     */
    function handleConfirmConnection(row: UserQueueStats) {
        console.log("Confirming user", row.id);
        let cur_user: UserRequest = {
            user_id: row.id,
        };
        confirmConnection(cur_user)
            .then((data) => {
                console.log(data);
                lastResponse = JSON.stringify(data);
            })
            .catch((err) => {
                console.error(err.message);
                lastResponse = JSON.stringify(err.message);
            });
    }

    // Refresh the queue's and its users' status every second
    setInterval(() => {
        refreshUsers();
    }, 1000);

    function refreshUsers() {
        // users = handleGetQueueStatus(); // To be implemented once endpoint is ready
        users = users.map((user) => {
            user.timeSinceJoin += 1;
            return user;
        });
    }
</script>

<div
    class="absolute top-0 left-0 right-0 flex flex-col items-center bg-gray-100"
>
    <div
        class="mt-6 relative bg-white pt-10 pb-2 px-2 shadow-xl ring-1 ring-gray-900/5 sm:mx-auto sm:max-w-lg sm:rounded-lg rounded"
    >
        <h1 class="text-xl font-bold mb-4 mx-6">Response</h1>
        <div
            class="relative bg-black pt-10 pb-8 px-4 ring-1 text-white ring-gray-900/5 sm:mx-auto sm:max-w-lg sm:rounded-lg rounded font-mono overflow-scroll"
        >
            {lastResponse}
        </div>
    </div>
    <div
        class="mt-6 relative bg-white px-6 pt-10 pb-8 shadow-xl ring-1 ring-gray-900/5 mx-2 sm:rounded-lg rounded"
    >
        <h1 class="text-xl font-bold mb-4">Admin</h1>
        <p>Simulate users entering, leaving, and timing out in the queue</p>
        <div class="flex space-x-2 my-4">
            <button
                class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded"
                on:click={handleAddUserToQueue}>Add to queue</button
            >
            <button
                class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded"
                on:click={handleGetMetrics}>Get Metrics</button
            >
        </div>
        <div>
            <SvelteTable {columns} rows={users} on:clickCell={handleClick} />
        </div>
    </div>
</div>
