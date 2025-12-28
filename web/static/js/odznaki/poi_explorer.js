// static/js/odznaki/poi_explorer.js

$(document).ready(function() {
    console.log('POI Explorer JS: Inicjalizacja...');

    // --- ZMIENNE GLOBALNE DLA CAŁEGO MODUŁU ---
    const form = $('#poi-explorer-form');
    const activeFiltersContainer = $('#active-filters-container');
    const regionSelects = $('.region-select');

    // --- INICJALIZACJA DATATABLES ---
    const poiTable = $('#poiExplorerTable').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: window.location.pathname,
            type: 'GET',
            data: function (d) {
                d.name = $('#filter-name').val();
                d.category = $('#filter-category').val();
                d.status = $('#filter-status').val();
                d.height_from = $('#filter-height-from').val();
                d.height_to = $('#filter-height-to').val();
                d.region = $('#final-region-filter').val();
                return d;
            }
        },
        columns: [
            { data: "name", render: (data, type, row) => `<a href="/poi/${row.id}/" class="app-link fw-bold">${data}</a>` },
            { data: "status", className: "text-center", render: function(data, type, row) { const status = data || 'nieaktywny'; let displayName = status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()); if (status === 'niezdobyty') displayName = 'Do zdobycia'; let badgeClass = 'bg-secondary'; if (status === 'zdobyty') badgeClass = 'bg-success'; else if (status === 'do_ponowienia') badgeClass = 'bg-primary'; else if (status === 'niezdobyty') badgeClass = 'bg-danger'; return `<span class="badge ${badgeClass}">${displayName}</span>`; }},
            { data: "height", className: "text-end", render: (data) => data ? `${data} m` : '-' },
            { data: "category" },
            { data: "mesoregion_name", render: (data, type, row) => data && row.mesoregion_id ? `<a href="/geography/region/mesoregion/${row.mesoregion_id}/" class="app-link small text-muted">${data}</a>` : (data || '-') },
            { data: "voivodeship_name", render: (data, type, row) => data && row.voivodeship_id ? `<a href="/geography/region/voivodeship/${row.voivodeship_id}/" class="app-link small text-muted">${data}</a>` : (data || '-') },
            { data: "last_visit_date", className: "text-center", render: function(data, type, row) { if (!data) return '-'; if (row.last_visit_trip_id) { return `<a href="/trip/${row.last_visit_trip_id}/" class="app-link small">${data}</a>`; } return `<span class="small">${data}</span>`; }}
        ],
        language: { url: "//cdn.datatables.net/plug-ins/1.13.7/i18n/pl.json" },
        pageLength: 25,
        order: [[ 0, "asc" ]],
        drawCallback: () => $('#page-loader')?.removeClass('show')
    });

    // --- FUNKCJE POMOCNICZE ---

    function updateExportLink() {
        const params = form.serialize();
        const exportUrl = `${window.location.pathname}?format=csv&${params}`;
        $('#export-csv-btn').attr('href', exportUrl);
    }

    function createPill(type, label, value) {
        return `<span class="badge bg-primary bg-opacity-10 text-primary border border-primary fw-normal">
                    <span class="opacity-75">${label}:</span> <strong>${value}</strong>
                    <a href="#" class="text-primary ms-1 text-decoration-none fw-bold remove-filter-btn" data-filter-type="${type}" title="Usuń ten filtr">×</a>
                </span>`;
    }

    function updateActiveFilterPills() {
        activeFiltersContainer.empty();
        let hasFilters = false;
        let filtersHtml = '';
        const nameVal = $('#filter-name').val(); if (nameVal) { filtersHtml += createPill('name', 'Nazwa', nameVal); hasFilters = true; }
        const categoryVal = $('#filter-category').val(); if (categoryVal) { const label = $(`#filter-category option[value="${categoryVal}"]`).text(); filtersHtml += createPill('category', 'Kategoria', label); hasFilters = true; }
        const statusVal = $('#filter-status').val(); if (statusVal) { const label = $(`#filter-status option[value="${statusVal}"]`).text(); filtersHtml += createPill('status', 'Status', label); hasFilters = true; }
        const heightFromVal = $('#filter-height-from').val(); if (heightFromVal) { filtersHtml += createPill('height_from', 'Wysokość od', `${heightFromVal} m`); hasFilters = true; }
        const heightToVal = $('#filter-height-to').val(); if (heightToVal) { filtersHtml += createPill('height_to', 'Wysokość do', `${heightToVal} m`); hasFilters = true; }
        const regionVal = $('#final-region-filter').val(); if (regionVal) { const lastActiveSelect = regionSelects.filter(function() { return $(this).val(); }).last(); if (lastActiveSelect.length) { const regionLabel = lastActiveSelect.find('option:selected').text(); const regionType = lastActiveSelect.data('region-type'); const regionTypeLabels = {'country': 'Kraj', 'province': 'Prowincja', 'subprovince': 'Podprowincja', 'macroregion': 'Makroregion', 'mesoregion': 'Mezoregion'}; filtersHtml += createPill('region', regionTypeLabels[regionType] || 'Region', regionLabel); hasFilters = true; }}
        if (hasFilters) {
            let finalHtml = `<div class="d-flex align-items-center flex-wrap gap-2"><span class="me-2"><small class="text-muted">Aktywne filtry:</small></span>${filtersHtml}<a href="#" class="ms-auto app-link small text-danger" id="clear-all-filters">Wyczyść wszystko</a></div>`;
            activeFiltersContainer.html(finalHtml).show();
        } else {
            activeFiltersContainer.hide();
        }
    }

    function updateUI() {
        poiTable.ajax.reload();
        updateActiveFilterPills();
        updateExportLink();
    }
    
    // --- LOGIKA FILTRÓW KASKADOWYCH ---
    regionSelects.on('change', function() {
        const selectedValue = $(this).val(); const regionType = $(this).data('region-type');
        const nextSelects = $(this).parent().nextAll().find('select.region-select');
        nextSelects.html('<option value="">Wybierz...</option>').prop('disabled', true);
        if (selectedValue) {
            $('#final-region-filter').val(`${regionType}:${selectedValue}`);
            const nextSelect = nextSelects.first();
            if (nextSelect.length) {
                $.getJSON(`/geography/subregions/${regionType}/${selectedValue}/`, function(data) {
                    if (data && data.length > 0) {
                        $.each(data, function(i, item) { nextSelect.append($('<option>', { value: item.id, text: item.name })); });
                        nextSelect.prop('disabled', false);
                    }
                });
            }
        } else {
            let lastActiveValue = '';
            $(this).parent().prevAll().find('select.region-select').each(function() {
                const prevVal = $(this).val(); if (prevVal) { lastActiveValue = `${$(this).data('region-type')}:${prevVal}`; return false; }
            });
            $('#final-region-filter').val(lastActiveValue);
        }
    });

    // --- OBSŁUGA EVENTÓW ---
    form.on('submit', (e) => { e.preventDefault(); updateUI(); });
    $('#reset-filters-btn').on('click', () => { form[0].reset(); regionSelects.not('#filter-country').html('<option value="">Wybierz...</option>').prop('disabled', true); $('#final-region-filter').val(''); updateUI(); });
    activeFiltersContainer.on('click', '.remove-filter-btn', function(e) {
        e.preventDefault(); const filterType = $(this).data('filter-type');
        if (filterType === 'region') { regionSelects.val(''); regionSelects.not('#filter-country').html('<option value="">Wybierz...</option>').prop('disabled', true); $('#final-region-filter').val(''); }
        else { $(`#filter-${filterType}, [name=${filterType}]`).val(''); }
        updateUI();
    });
    activeFiltersContainer.on('click', '#clear-all-filters', (e) => { e.preventDefault(); $('#reset-filters-btn').click(); });
    
    // --- PIERWSZE WYWOŁANIE ---
    updateActiveFilterPills();
    updateExportLink();
});