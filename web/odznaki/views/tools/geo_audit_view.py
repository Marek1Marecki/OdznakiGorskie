# odznaki/views/tools/geo_audit_view.py
from django.shortcuts import render
from django.core.paginator import Paginator
from django.core.cache import cache  # <-- Dodajemy import cache'u
from odznaki.services import point_of_interest_service


def geo_audit_view(request):
    """
    Widok dla narzędzia do audytu spójności geograficznej,
    z inteligentnym cache'owaniem wyników.
    """
    cache_key = 'geo_audit_results'

    # Krok 1: Spróbuj pobrać wyniki z cache'u
    all_problems = cache.get(cache_key)

    # Krok 2: Jeśli w cache'u nic nie ma, wykonaj "ciężką" pracę
    if all_problems is None:
        print("DEBUG: Uruchamiam pełny audyt geograficzny (cache miss)...")
        # Wykonaj pełen audyt
        all_problems = point_of_interest_service.run_full_geo_audit(request)

        # Zapisz wyniki w cache'u na 1 godzinę (3600 sekund)
        cache.set(cache_key, all_problems, 3600)
    else:
        print("DEBUG: Używam wyników audytu z cache'u (cache hit)...")

    # Krok 3: Zastosuj paginację do (potencjalnie cache'owanych) wyników
    if all_problems:
        paginator = Paginator(all_problems, 10)  # Pokaż 10 problemów na stronę
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
    else:
        page_obj = None

    context = {
        'problematic_pois_page': page_obj,
    }

    return render(request, 'odznaki/tools/geo_audit.html', context)
