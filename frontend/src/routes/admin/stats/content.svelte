<script lang="ts">
    import AdminChart from "$lib/admin_cmpnts/AdminChart.svelte";
    import AdminTable from "$lib/admin_cmpnts/AdminTable.svelte";
    import { getStatus } from "$lib/queue";
    import { getUsers } from "$lib/queue";
    import type { QueueStatus, UserRequest } from "$lib/types";
    import { Button } from "flowbite-svelte";
    import { onMount } from "svelte";
    import { joinQueue } from "$lib/queue";

    let test_data = {
        name: "test",
        data: [1, 5, 3, 10],
        color: "#1C64F2",
    };

    let columns = [
        {
            label: "ID",
            key: "user_id",
        },
        {
            label: "Status",
            key: "status",
        },
        {
            label: "Position",
            key: "position",
        }
    ];
    let users: {
        active_users: QueueStatus[];
        draft_users: QueueStatus[];
        waiting_users: QueueStatus[];
    } = {
        active_users: [],
        draft_users: [],
        waiting_users: [],
    };

    async function fetchCurQueueStatus() {
        try {
            const data = await getUsers();

            users.active_users = await Promise.all(
                data.active_users.map(
                    async (user_id: string) => await getStatus(user_id)
                )
            );

            users.draft_users = await Promise.all(
                data.draft_users.map(
                    async (user_id: string) => await getStatus(user_id)
                )
            );

            users.waiting_users = await Promise.all(
                data.waiting_users.map(
                    async (user_id: string) => await getStatus(user_id)
                )
            );
        } catch (error) {
            console.error("Error fetching queue status:", error);
        }
    }

    setInterval(() => {
        fetchCurQueueStatus();
    }, 5000);

    onMount(() => {
        fetchCurQueueStatus();
    });

    /**
     * Generates a random user to join the queue.
     *
     * @returns A UserRequest object with the generated user's random user_id.
     */
    function generateRandomUser() {
        let new_user_request: UserRequest = {
            user_id: Math.random().toString(36).substring(2, 9),
        };
        return new_user_request;
    }

    /**
     * Adds a randomly generated user to the queue.
     */
    function handleAddSimulatedUserToQueue() {
        let user = generateRandomUser();
        console.log("Adding user to queue");
        joinQueue(user)
            .then((data) => {
                console.log(data);
                fetchCurQueueStatus();
            })
            .catch((err) => {
                console.error(err.message);
            });
        
    }
</script>

<div class="w-full p-4 h-screen overflow-y-auto">
    <div class="grid grid-cols-3 gap-4 mb-4">
        <Button color="alternative" on:click={handleAddSimulatedUserToQueue}
            >Add simulated user</Button
        >
    </div>

    <div class="grid grid-cols-2 gap-4 mb-4">
        <div class="w-full">
            <AdminChart
                main_value="2"
                unit="test"
                chart_data={test_data}
                height="200px"
                show_graph={true}
            />
        </div>
        <AdminChart
            main_value="2"
            unit="test"
            chart_data={test_data}
            height="200px"
            show_graph={true}
        />
    </div>
    <div class="grid grid-cols-2 gap-4 mb-4">
        <AdminTable {columns} data={users.active_users} />
        <div class="col-span-2">
            <AdminTable {columns} data={users.draft_users} />
        </div>
        <AdminTable {columns} data={users.draft_users} />
        <AdminTable {columns} data={users.draft_users} />
        <AdminTable {columns} data={users.draft_users} />
        <AdminTable {columns} data={users.waiting_users} />
    </div>

</div>
