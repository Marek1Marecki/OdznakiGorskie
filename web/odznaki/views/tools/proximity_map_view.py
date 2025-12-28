# odznaki/views/tools/proximity_map_view.py
from django.shortcuts import render
from odznaki.models import PointOfInterest
# NIE potrzebujemy już `find_proximal_poi_groups`
from odznaki.utils.map_utils import create_proximity_group_map


def proximity_group_map_view(request):
    """
    Widok, który renderuje mapę dla grupy POI o podanych ID.
    Wersja 2.0: Prosta i niezawodna.
    """
    poi_ids_str = request.GET.get('poi_ids', '')
    if not poi_ids_str:
        return render(request, 'odznaki/tools/_proximity_map_embed.html', {'map_html': None})

    try:
        poi_ids = [int(pid) for pid in poi_ids_str.split(',') if pid.isdigit()]
    except (ValueError, TypeError):
        return render(request, 'odznaki/tools/_proximity_map_embed.html', {'map_html': None})

    # --- NOWA, UPROSZCZONA LOGIKA ---
    # 1. Pobierz z bazy tylko te POI, których potrzebujemy
    pois_in_group = list(PointOfInterest.objects.filter(id__in=poi_ids).select_related('parent'))

    # 2. Przygotuj dane w formacie, którego oczekuje kreator mapy
    # (musimy ręcznie odtworzyć strukturę `analyzed_pois`)
    group_id_set = set(poi_ids)
    analyzed_pois_for_map = []
    for poi in pois_in_group:
        status = ''
        if poi.parent is None:
            status = 'Rodzic'
        # Sprawdzamy, czy rodzic jest RÓWNIEŻ w tej grupie
        elif poi.parent_id in group_id_set:
            status = 'Połączony'
        else:
            status = 'Błędne połączenie'

        analyzed_pois_for_map.append({'poi': poi, 'link_status': status})
    # --- KONIEC NOWEJ LOGIKI ---

    map_html = None
    if analyzed_pois_for_map:
        map_html = create_proximity_group_map(
            analyzed_pois_for_map, request
        )

    return render(request, 'odznaki/tools/_proximity_map_embed.html', {'map_html': map_html})
