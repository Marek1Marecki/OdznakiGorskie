// static/js/odznaki/yearly_stats.js
document.addEventListener('DOMContentLoaded', function() {
    const staticPrefix = document.getElementById('js-config')?.dataset.staticPrefix || '';

    // --- Inicjalizacja DataTables ---
    $('#yearlyStatsTable').DataTable({
        "language": { "url": `${staticPrefix}datatables/i18n/pl.json` },
        "pageLength": 10, "searching": false, "lengthChange": false, "info": false,
        "order": [[ 0, "desc" ]]
    });

    // --- Logika dla interaktywnego wykresu ---
    const chartDataElement = document.getElementById('chart-data-json');
    if (!chartDataElement) return;

    const chartData = JSON.parse(chartDataElement.textContent);
    const ctx = document.getElementById('yearlyChart').getContext('2d');

    const dataConfigs = {
        distance: { label: 'Dystans (km)', data: chartData.distance, color: 'rgba(54, 162, 235, 1)', unit: 'km' },
        elevation: { label: 'Suma podejść (m)', data: chartData.elevation, color: 'rgba(255, 159, 64, 1)', unit: 'm' },
        got_points: { label: 'Punkty GOT', data: chartData.got_points, color: 'rgba(75, 192, 192, 1)', unit: 'pkt' },
        new_pois: { label: 'Nowe POI', data: chartData.new_pois, color: 'rgba(153, 102, 255, 1)', unit: '' },
        trips: { label: 'Liczba wycieczek', data: chartData.trips, color: 'rgba(255, 99, 132, 1)', unit: '' },
        everest: { label: 'Suma "Everest" (m)', data: chartData.everest, color: 'rgba(201, 203, 207, 1)', unit: 'm' },
        regions: { label: 'Odwiedzone regiony', data: chartData.regions, color: 'rgba(255, 205, 86, 1)', unit: '' },
        badges: { label: 'Zdobyte odznaki', data: chartData.badges, color: 'rgba(40, 167, 69, 1)', unit: '' }
    };

    const yearlyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: chartData.labels,
            datasets: [{
                label: dataConfigs.distance.label,
                data: dataConfigs.distance.data,
                backgroundColor: dataConfigs.distance.color.replace('1)', '0.6)'),
                borderColor: dataConfigs.distance.color,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: { y: { beginAtZero: true } },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) { label += ': '; }
                            if (context.parsed.y !== null) {
                                const currentType = document.querySelector('input[name="chart-type"]:checked').value;
                                const unit = dataConfigs[currentType].unit;
                                label += `${context.parsed.y} ${unit}`;
                            }
                            return label;
                        }
                    }
                }
            }
        }
    });

    document.getElementById('chartDataType').addEventListener('change', function(event) {
        const selectedType = event.target.value;
        const config = dataConfigs[selectedType];
        yearlyChart.data.datasets[0].data = config.data;
        yearlyChart.data.datasets[0].label = config.label;
        yearlyChart.data.datasets[0].backgroundColor = config.color.replace('1)', '0.6)');
        yearlyChart.data.datasets[0].borderColor = config.color;
        yearlyChart.update();
    });
});