// static/js/odznaki/csv_export_button.js

document.addEventListener('DOMContentLoaded', function() {
    // Znajdź formularz z filtrami i przycisk eksportu na stronie
    const filterForm = document.getElementById('badge-filter-form') || document.getElementById('filter-form');
    const exportBtn = document.getElementById('export-csv-btn');

    // Jeśli któregoś z elementów brakuje, nie rób nic
    if (!filterForm || !exportBtn) {
        return;
    }

    function updateExportLink() {
        // Zbierz wszystkie parametry z formularza w formacie URL
        const params = new URLSearchParams(new FormData(filterForm)).toString();

        // Zbuduj nowy URL do eksportu i ustaw go jako atrybut href
        exportBtn.href = `${window.location.pathname}?format=csv&${params}`;
    }

    // Aktualizuj link za każdym razem, gdy zmieni się coś w formularzu
    filterForm.addEventListener('change', updateExportLink);

    // Ustaw poprawny link również przy pierwszym załadowaniu strony
    updateExportLink();
});
