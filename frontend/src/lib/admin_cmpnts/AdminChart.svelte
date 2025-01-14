<script>
    import {
        Chart,
        Card,
        A,
        Button,
        Dropdown,
        DropdownItem,
    } from "flowbite-svelte"; 
    let { main_value, unit, chart_data, height, show_graph } = $$props;

    let options = {
        chart: {
            height: height,
            maxWidth: "100%",
            type: "area",
            fontFamily: "Inter, sans-serif",
            dropShadow: {
                enabled: false,
            },
            toolbar: {
                show: false,
            },
        },
        tooltip: {
            enabled: true,
            x: {
                show: false,
            },
        },
        fill: {
            type: "gradient",
            gradient: {
                opacityFrom: 0.55,
                opacityTo: 0,
                shade: "#1C64F2",
                gradientToColors: ["#1C64F2"],
            },
        },
        dataLabels: {
            enabled: false,
        },
        stroke: {
            width: 6,
        },
        grid: {
            show: false,
            strokeDashArray: 4,
            padding: {
                left: 2,
                right: 2,
                top: 0,
            },
        },
        series: [chart_data],
        xaxis: {
            
            labels: {
                show: false,
            },
            axisBorder: {
                show: false,
            },
            axisTicks: {
                show: false,
            },
        },
        yaxis: {
            show: false,
        },
    };

    if (!show_graph) {
        options.chart.height = "0px";
    }
</script>

<!-- TODO Could end up throwing an error if chart_data is undefined -->
{#if chart_data.data && chart_data.data.length > 0}
<div class="test">
    <Card class="max-w-none">
        <div class="flex justify-between">
            <div>
                <h5
                    class="leading-none text-3xl font-bold text-gray-900 dark:text-white pb-2"
                >
                    {main_value}
                </h5>
                <p
                    class="text-base font-normal text-gray-500 dark:text-gray-400"
                >
                    {unit}
                </p>
            </div>
        </div>
        <Chart {options} />
    </Card>
</div>
{/if}
