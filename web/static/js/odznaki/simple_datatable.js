// static/js/odznaki/simple_datatable.js
$(document).ready(function() {
    const staticPrefix = document.getElementById('js-config')?.dataset.staticPrefix || '';
    // Inicjalizuj wszystkie tabele, które mają klasę .datatable-simple
    $('.datatable-simple').DataTable({
        "language": { "url": `${staticPrefix}datatables/i18n/pl.json` },
        "pageLength": 25,
        "order": []
    });
});