<script>
    import AdminTimeline from "$lib/admin_cmpnts/AdminTimeline.svelte";
    import AdminChart from "$lib/admin_cmpnts/AdminChart.svelte";
    import AdminWarning from "$lib/admin_cmpnts/AdminWarning.svelte";

    let test_data = {
        name: "Users",
        data: [1, 5, 3, 10],
        color: "#1C64F2",
    };
</script>

<div class="w-full p-4 h-screen overflow-y-auto">
    <AdminTimeline />
    <!-- TODO review the way the main value is fetched -->
    <AdminChart
        main_value="{Math.max(...test_data.data)}"
        unit="Users speaking to Lucie"
        chart_data={test_data}
        height="200px"
        show_graph={false}
    />
</div>
