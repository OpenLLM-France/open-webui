<script lang="ts">
    import { Timeline } from "flowbite-svelte";
    import AdminTimelineElement from "./AdminTimelineElement.svelte";

    let data = [
        {
            title: "First event",
            date: "2021-09-01",
            description: "This is the first event that happened.",
        },
        {
            title: "Second event",
            date: "2021-09-02",
            description: "This is the second event that happened.",
        },
        {
            title: "Third event",
            date: "2021-09-03",
            description: "This is the third event that happened.",
        },
    ];
</script>

<Timeline>
    {#each data.reverse() as { title, date, description }}
        <AdminTimelineElement {title} {date} {description} />
    {/each}
</Timeline>
