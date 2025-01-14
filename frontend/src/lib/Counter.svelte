<script lang="ts">
    let count = 0;

    function increment() {
        count++;
    }
</script>

<button onclick={increment}>
    {count}
</button> 