<script>
    import AdminSidebar from "$lib/admin_cmpnts/AdminSidebar.svelte";
    import Content from "./content.svelte";
</script>

<div class="min-h-screen dark:bg-gray-900">
    <div class="flex">
        <AdminSidebar />
        <Content />
    </div>
</div>

<style>
    /* Les styles sont gérés par Tailwind CSS */
</style>
