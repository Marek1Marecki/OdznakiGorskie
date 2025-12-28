document.addEventListener('DOMContentLoaded', function() {
    // Inicjalizacja Tooltipów
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"], [data-bs-toggle-tooltip="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) { return new bootstrap.Tooltip(tooltipTriggerEl); });

    // Inicjalizacja Modala
    const imageModal = document.getElementById('imageModal');
    if (imageModal) {
        imageModal.addEventListener('show.bs.modal', function (event) {
            const triggerElement = event.relatedTarget;
            const modalImage = document.getElementById('modalImage'); // Zmiana
            modalImage.src = triggerElement.getAttribute('data-img-src');
            imageModal.querySelector('.modal-title').textContent = triggerElement.getAttribute('data-img-title');
        });
    }

    // --- Logika Spinera (Wersja Ostateczna - Delegacja Zdarzeń) ---
    const pageLoader = document.getElementById('page-loader');
    if (pageLoader) {
        function showLoader() {
            pageLoader.classList.add('show');
        }

        // Funkcja do sprawdzania, czy link jest "bezpieczny" (nie powinien wywoływać spinera)
        function isSafeLink(element) {
            const href = element.getAttribute('href');
            // Sprawdź, czy to link do otwarcia w nowej karcie
            if (element.getAttribute('target') === '_blank') return true;
            // Sprawdź, czy to komponent Bootstrapa (modal, dropdown, etc.)
            if (element.hasAttribute('data-bs-toggle')) return true;
            // Sprawdź, czy to link-kotwica na tej samej stronie
            if (href && href.startsWith('#')) return true;
            // Sprawdź, czy to link JavaScript (bardzo rzadkie, ale bezpieczniej)
            if (href && href.toLowerCase().startsWith('javascript:')) return true;

            return false;
        }

        // Podepnij event listener do całego `body` dla kliknięć
        document.body.addEventListener('click', function(e) {
            // Znajdź najbliższy kliknięty link (nawet jeśli kliknięto ikonkę wewnątrz linku)
            const link = e.target.closest('a');

            // Jeśli to jest link i nie jest "bezpieczny", pokaż spiner
            if (link && link.href && !isSafeLink(link)) {
                showLoader();
            }
        });

        // Podepnij event listener do całego `body` dla formularzy
        document.body.addEventListener('submit', function(e) {
            const form = e.target.closest('form');
            // Pokaż spiner, chyba że formularz ma specjalny atrybut `data-no-spinner`
            if (form && !form.hasAttribute('data-no-spinner')) {
                showLoader();
            }
        });

        // Logika ukrywania spinera (bez zmian)
        window.addEventListener('load', () => setTimeout(() => pageLoader.classList.remove('show'), 100));
        window.addEventListener('pageshow', (event) => {
            if (event.persisted) {
                pageLoader.classList.remove('show');
            }
        });
    }
});