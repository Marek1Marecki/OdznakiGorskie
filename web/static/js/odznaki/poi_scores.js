// static/js/odznaki/poi_scores.js
$(document).ready(function() {
    $('#poiRankingTable').DataTable({
        "processing": true,
        "serverSide": true,
        "ajax": {
            "url": "/scores/poi/",
            "type": "GET"
        },
        "columns": [
            {
                "data": null, "orderable": false, "searchable": false,
                "render": function (data, type, row, meta) { return meta.row + meta.settings._iDisplayStart + 1; }
            },
            {
                "data": "name",
                "render": function (data, type, row) { return `<a href="/poi/${row.id}/" class="app-link fw-bold">${data}</a>`; }
            },
            {
                "data": "mesoregion",
                "render": function (data, type, row) {
                    return data ? `<a href="/geography/region/mesoregion/${row.mesoregion_id}/" class="app-link small text-muted">${data}</a>` : '-';
                }
            },
            {
                "data": "voivodeship",
                "render": function (data, type, row) {
                    return data ? `<a href="/geography/region/voivodeship/${row.voivodeship_id}/" class="app-link small text-muted">${data}</a>` : '-';
                }
            },
            {
                "data": "score", "className": "text-center",
                "render": function (data, type, row) { return `<span class="badge bg-primary rounded-pill fs-6">${Math.round(data)} pkt</span>`; }
            },
            {
                "data": "badges", "orderable": false, "searchable": false,
                "render": function (data, type, row) {
                    // Ta logika zależy od danych z backendu, na razie zakładamy, że ich nie ma
                    return '';
                }
            }
        ],
        "language": { "url": "//cdn.datatables.net/plug-ins/1.13.7/i18n/pl.json" },
        "pageLength": 25,
        "order": [[ 4, "desc" ]]
    });
});