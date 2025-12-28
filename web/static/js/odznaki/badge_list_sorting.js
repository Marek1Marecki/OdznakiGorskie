// static/js/odznaki/badge_list_sorting.js
document.addEventListener('DOMContentLoaded', function() {
    const filterForm = document.getElementById('badge-filter-form');
    const sortSelect = document.getElementById('sort');
    const sortableHeaders = document.querySelectorAll('.sortable-header');

    if (!filterForm || !sortSelect) {
        return;
    }

    // Mapa do przechowywania kierunku sortowania dla każdej kolumny
    const sortDirections = {
        'name_asc': 'name_desc',
        'name_desc': 'name_asc',
        'organizer_asc': 'organizer_desc',
        'organizer_desc': 'organizer_asc',
        'progress_desc': 'progress_asc',
        'progress_asc': 'progress_desc'
    };

    // Funkcja do aktualizacji ikon sortowania
    function updateSortIcons() {
        const currentSort = sortSelect.value;
        
        sortableHeaders.forEach(header => {
            const icon = header.querySelector('i');
            const headerSort = header.getAttribute('data-sort');
            
            if (icon) {
                // Sprawdź czy ta kolumna jest aktualnie sortowana
                // Porównaj prefiks (np. 'name', 'organizer', 'progress')
                const currentPrefix = currentSort.split('_')[0];
                const headerPrefix = headerSort.split('_')[0];
                
                if (currentPrefix === headerPrefix) {
                    // Pokaż odpowiednią ikonę
                    if (currentSort.includes('desc')) {
                        icon.className = 'fas fa-sort-down ms-1';
                        icon.style.opacity = '1';
                    } else {
                        icon.className = 'fas fa-sort-up ms-1';
                        icon.style.opacity = '1';
                    }
                } else {
                    // Ukryj ikonę dla nieaktywnych kolumn
                    icon.className = 'fas fa-sort ms-1';
                    icon.style.opacity = '0.5';
                }
            }
        });
    }

    // Obsługa klikania na nagłówki kolumn
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function(e) {
            // Nie reaguj na klikanie na linki wewnątrz nagłówka
            if (e.target.tagName === 'A') {
                return;
            }

            const headerSort = this.getAttribute('data-sort');
            const currentSort = sortSelect.value;
            
            // Sprawdź czy klikamy na tę samą kolumnę
            const currentPrefix = currentSort.split('_')[0];
            const headerPrefix = headerSort.split('_')[0];
            
            if (currentPrefix === headerPrefix) {
                // Jeśli klikamy na tę samą kolumnę, zmień kierunek sortowania
                const newSort = sortDirections[currentSort];
                sortSelect.value = newSort;
            } else {
                // Jeśli klikamy na inną kolumnę, ustaw jej sortowanie
                sortSelect.value = headerSort;
            }
            
            // Aktualizuj ikony
            updateSortIcons();
            
            // Wyślij formularz
            filterForm.submit();
        });
    });

    // Aktualizuj ikony przy załadowaniu strony
    updateSortIcons();
});
