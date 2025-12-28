// static/js/odznaki/profile_stats.js
document.addEventListener('DOMContentLoaded', function() {
    const chartDataByPoiElement = document.getElementById('chart-data-by-poi');
    const chartDataByTripElement = document.getElementById('chart-data-by-trip');

    if (!chartDataByPoiElement || !chartDataByTripElement) return;

    const chartDataByPoi = JSON.parse(chartDataByPoiElement.textContent);
    const chartDataByTrip = JSON.parse(chartDataByTripElement.textContent);

    const colorPalette = [
        'rgba(54, 162, 235, 0.8)', 'rgba(255, 99, 132, 0.8)', 'rgba(255, 206, 86, 0.8)',
        'rgba(75, 192, 192, 0.8)', 'rgba(153, 102, 255, 0.8)', 'rgba(255, 159, 64, 0.8)',
        'rgba(100, 100, 100, 0.8)', 'rgba(200, 50, 50, 0.8)', 'rgba(50, 200, 50, 0.8)',
        'rgba(50, 50, 200, 0.8)'
    ];

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    padding: 20,
                    generateLabels: function(chart) {
                        const data = chart.data;
                        if (data.labels.length && data.datasets.length) {
                            const sum = data.datasets[0].data.reduce((a, b) => a + b, 0);
                            return data.labels.map((label, i) => {
                                const value = data.datasets[0].data[i];
                                const percentage = sum > 0 ? ((value / sum) * 100).toFixed(1) : 0;
                                return {
                                    text: `${label} (${percentage}%)`,
                                    fillStyle: data.datasets[0].backgroundColor[i],
                                    hidden: isNaN(data.datasets[0].data[i]) || chart.getDatasetMeta(0).data[i].hidden,
                                    index: i
                                };
                            });
                        }
                        return [];
                    }
                }
            },
            tooltip: { callbacks: { label: function(context) { return ` ${context.label}: ${context.raw}`; } } }
        }
    };

    const poiChartCtx = document.getElementById('poiChart').getContext('2d');
    const poiChart = new Chart(poiChartCtx, {
        type: 'doughnut',
        data: {
            labels: chartDataByPoi.province.labels,
            datasets: [{ data: chartDataByPoi.province.data, backgroundColor: colorPalette }]
        },
        options: chartOptions
    });

    const tripChartCtx = document.getElementById('tripChart').getContext('2d');
    const tripChart = new Chart(tripChartCtx, {
        type: 'doughnut',
        data: {
            labels: chartDataByTrip.province.labels,
            datasets: [{ data: chartDataByTrip.province.data, backgroundColor: colorPalette }]
        },
        options: chartOptions
    });

    function updateDashboard(level) {
        $('.top-list-container').hide();
        $(`#top5-poi-${level}`).show();
        $(`#top5-trip-${level}`).show();

        poiChart.data.labels = chartDataByPoi[level].labels;
        poiChart.data.datasets[0].data = chartDataByPoi[level].data;
        poiChart.update();

        tripChart.data.labels = chartDataByTrip[level].labels;
        tripChart.data.datasets[0].data = chartDataByTrip[level].data;
        tripChart.update();
    }

    document.getElementById('chartHierarchyLevel').addEventListener('change', function(event) {
        const selectedLevel = event.target.value;
        updateDashboard(selectedLevel);
    });
});