# odznaki/views/tools/poi_proximity_view.py

from django.shortcuts import render
from odznaki.services.point_of_interest_service import find_proximal_poi_groups
from odznaki.utils.map_utils import create_proximity_group_map


def proximity_tool_view(request):
    """
    Widok dla narzędzia do analizy bliskości i powiązań punktów POI.
    """
    # 1. Pobierz WSZYSTKIE grupy (to jest "źródło prawdy")
    all_groups = find_proximal_poi_groups()

    # 2. Pobierz parametry filtrowania i sortowania
    status_filter = request.GET.get('status_filter', 'all')
    sort_by = request.GET.get('sort', 'distance_asc')

    # --- POPRAWKA JEST TUTAJ: Obliczamy statystyki PRZED filtrowaniem ---
    problems_count = sum(1 for g in all_groups if g['group_status'] == 'Wymaga uwagi')
    ok_count = len(all_groups) - problems_count
    # --- KONIEC POPRAWKI ---

    # 3. Zastosuj filtrowanie do wyświetlenia
    if status_filter == 'problems_only':
        display_groups = [group for group in all_groups if group['group_status'] == 'Wymaga uwagi']
    elif status_filter == 'ok_only':
        display_groups = [group for group in all_groups if group['group_status'] == 'OK']
    else:
        display_groups = all_groups

    # 4. Zastosuj sortowanie
    sort_key = 'max_distance' if 'distance' in sort_by else 'poi_count'
    reverse_sort = '_desc' in sort_by
    display_groups.sort(key=lambda g: g[sort_key], reverse=reverse_sort)

    # 5. Przygotuj dane dla szablonu (dla iframe)
    for group in display_groups:
        group['poi_ids_str'] = ','.join(str(item['poi'].id) for item in group['pois_in_group'])

    # 6. Zbuduj finalny kontekst
    context = {
        'poi_groups': display_groups,
        'total_group_count': len(all_groups),
        'problems_group_count': problems_count,
        'ok_group_count': ok_count,
        'current_filters': {
            'status': status_filter,
            'sort': sort_by,
        }
    }

    return render(request, 'odznaki/tools/proximity_tool.html', context)
