// static/js/odznaki/region_detail.js

document.addEventListener('DOMContentLoaded', function() {
    const staticPrefix = document.getElementById('js-config')?.dataset.staticPrefix || '';
    const poiTab = document.getElementById('poi-tab');
    if (!poiTab) return;

    let table = null;
    poiTab.addEventListener('shown.bs.tab', function() {
        if (table) return;
        table = $('#poi-table').DataTable({
            language: { url: `${staticPrefix}datatables/i18n/pl.json` },
            pageLength: 25,
            lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "Wszystkie"]],
            order: [[2, 'desc']],
            responsive: true,
            initComplete: function() {
                this.api().columns([0, 3, 4]).every(function() {
                    const column = this;
                    const filterCell = $('.filter-row th').eq(column.index());
                    if (filterCell.text().includes('Filtruj')) {
                        const select = $(`<select class="form-select form-select-sm"><option value="">Wszystkie</option></select>`)
                            .appendTo(filterCell.empty())
                            .on('change', function () {
                                column.search($(this).val(), false, false).draw();
                            });

                        column.data().unique().sort().each(function (d, j) {
                            const val = $(d).text().trim();
                            if (val) select.append('<option value="' + val + '">' + val + '</option>');
                        });
                    }
                });
            }
        });
    });
});