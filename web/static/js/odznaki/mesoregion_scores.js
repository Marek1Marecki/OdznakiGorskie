// static/js/odznaki/mesoregion_scores.js
$(document).ready(function() {
    $('#regionRankingTable').DataTable({
        "processing": true,
        "serverSide": true,
        "ajax": {
            "url": "/scores/region/", // Używamy "hardcoded" URL, bo jest stały
            "type": "GET"
        },
        "columns": [
            {
                "data": null, "orderable": false, "searchable": false,
                "render": function (data, type, row, meta) { return meta.row + meta.settings._iDisplayStart + 1; }
            },
            {
                "data": "mesoregion_name",
                "render": function (data, type, row) {
                    return row.mesoregion_id ? `<a href="/geography/region/mesoregion/${row.mesoregion_id}/" class="app-link fw-bold">${data}</a>` : data;
                }
            },
            {
                "data": "total_score", "className": "text-center",
                "render": function(data, type, row) { return `<span class="badge bg-primary rounded-pill fs-6">${Math.round(data)} pkt</span>`; }
            },
            { "data": "poi_count", "className": "text-center" },
            {
                "data": "top_pois", "orderable": false, "searchable": false,
                "render": function(data, type, row) {
                    if (!Array.isArray(data) || data.length === 0) return '-';
                    let links = data.map(poi_item => {
                        return `<a href="/poi/${poi_item.id}/" class="app-link text-muted">${poi_item.name}</a> (${Math.round(poi_item.score)} pkt)`;
                    });
                    return links.join(', ');
                }
            }
        ],
        "language": { "url": "//cdn.datatables.net/plug-ins/1.13.7/i18n/pl.json" },
        "pageLength": 25,
        "order": [[ 1, 'desc' ]] // Sortowanie po total_score
    });
});