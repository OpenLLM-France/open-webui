<script>
    import { Timeline, TimelineItem, Button } from "flowbite-svelte";

    let { title, date, description } = $props();
</script>

<TimelineItem {title} {date}>
    <p class="mb-4 text-base font-normal text-gray-500 dark:text-gray-400">
        {description}
    </p>
</TimelineItem>
