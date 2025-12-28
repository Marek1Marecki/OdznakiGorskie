# odznaki/views/geography_views.py

from datetime import date
from collections import Counter
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.db.models import Prefetch, Count, Q, When, Case, Value, F
from django.db import models
from django.db.models.functions import Coalesce
from django.contrib.gis.db.models.functions import Union

from odznaki.constants import MOUNTAIN_RANGES
from odznaki.models import (
    Country, Province, SubProvince, MacroRegion, MesoRegion, Voivodeship, PointOfInterest,
    BadgeRequirement, Visit
)
from odznaki.services.point_of_interest_service import calculate_poi_statuses
from odznaki.services.scoring_service import calculate_scores_for_queryset
from odznaki.services import geography_service
from odznaki.utils.geo_helpers import get_breadcrumbs
from odznaki.utils.map_utils import create_region_map_with_folium


# Słownik hierarchii pozostaje bez zmian
HIERARCHY = {
    'country': (Country, ['provinces', 'voivodeships']),
    'province': (Province, ['subprovinces']),
    'subprovince': (SubProvince, ['macroregions']),
    'macroregion': (MacroRegion, ['mesoregions']),
    'mesoregion': (MesoRegion, []),
    'voivodeship': (Voivodeship, []),
}


def geography_index_view(request):
    """
    Strona główna geografii - wyświetla listy krajów, województw i łańcuchów górskich.
    Wersja 2.0: Z sortowaniem województw i licznikiem POI dla łańcuchów.
    """
    # 1. Pobierz listę krajów (bez zmian)
    countries = Country.objects.annotate(
        poi_count=Count('points_of_interest_country')
    ).order_by('order', 'name')

    # 2. Pobierz listę wszystkich województw
    voivodeships_qs = Voivodeship.objects.select_related('country').annotate(
        poi_count=Count('points_of_interest_admin')
    )

    # --- ZMIANA: Sortujemy po liczbie POI, malejąco ---
    voivodeships = voivodeships_qs.order_by('-poi_count', 'name')

    # --- NOWA LOGIKA: Obliczanie liczby POI dla łańcuchów górskich ---
    mountain_ranges_with_stats = []
    for slug, config in MOUNTAIN_RANGES.items():
        # Budujemy dynamiczne zapytanie na podstawie definicji w constants.py
        query = Q()
        if config.get('province_ids'):
            query |= Q(province_id__in=config['province_ids'])
        if config.get('subprovince_ids'):
            query |= Q(subprovince_id__in=config['subprovince_ids'])
        if config.get('macroregion_ids'):
            query |= Q(macroregion_id__in=config['macroregion_ids'])

        # Wykonujemy szybkie zapytanie COUNT
        if query:
            poi_count = PointOfInterest.objects.filter(query).count()
        else:
            poi_count = 0

        # Kopiujemy oryginalną konfigurację i dodajemy do niej nową daną
        range_data = config.copy()
        range_data['poi_count'] = poi_count
        mountain_ranges_with_stats.append(range_data)

    context = {
        'countries': countries,
        'voivodeships': voivodeships,
        'mountain_ranges': mountain_ranges_with_stats,  # <-- Przekazujemy nową, wzbogaconą listę
    }

    return render(request, 'odznaki/geography/geography_index.html', context)


# @cache_page(60 * 15)
def geography_region_detail_view(request, model_name, pk):
    """
    Wersja 7.0: Użycie `POIStatusCalculator` zamiast `annotate` dla 100% spójności statusów.
    """
    if model_name not in HIERARCHY:
        raise Http404("Nieznany typ regionu geograficznego.")

    model_class, children_relations = HIERARCHY[model_name]

    region_object = get_object_or_404(model_class, pk=pk)
    # ... (logika pobierania children_data, breadcrumbs bez zmian) ...
    children_data = {}
    for relation_name in children_relations:
        child_model = model_class._meta.get_field(relation_name).related_model
        queryset = child_model.objects.filter(**{model_name: pk})
        children_data[relation_name] = {'queryset': list(queryset), 'counts': {},
                                        'verbose_name_plural': queryset.model._meta.verbose_name_plural}
    breadcrumbs = get_breadcrumbs(region_object)
    parent_regions = breadcrumbs[:-1] if len(breadcrumbs) > 1 else []

    # --- GŁÓWNA ZMIANA W LOGICE POBIERANIA POI ---
    all_pois_in_region_qs = geography_service.get_pois_for_region(region_object)

    # Zamiast `_annotate_pois_with_status`, teraz używamy `prefetch_related`,
    # aby przygotować dane dla `POIStatusCalculator`.
    pois_qs_optimized = all_pois_in_region_qs.select_related(
        'mesoregion', 'voivodeship', 'country'
    ).defer(
        'mesoregion__shape', 'voivodeship__shape', 'country__shape'
    ).prefetch_related(
        'visits',  # Potrzebne dla kalkulatora
        Prefetch(
            'badge_requirements',  # Potrzebne dla kalkulatora
            queryset=BadgeRequirement.objects.select_related('badge')
        )
    )
    # --- KONIEC GŁÓWNEJ ZMIANY ---

    # Logika flag pozostaje bez zmian
    total_pois_count_for_threshold = all_pois_in_region_qs.count()  # Używamy szybkiego count()
    POI_THRESHOLD = 500
    if 'show_map' in request.GET:
        show_map = request.GET.get('show_map') == '1'
    else:
        show_map = total_pois_count_for_threshold <= POI_THRESHOLD
    show_pois_param = request.GET.get('show_pois', '0') == '1'
    show_neighbors_param = request.GET.get('show_neighbors', '0') == '1'
    show_heatmap = show_map
    show_pois = show_pois_param
    show_neighbors = show_neighbors_param

    if not show_map and not show_pois:
        pois_qs_optimized = pois_qs_optimized.defer('location')

    all_pois_list = list(pois_qs_optimized)
    total_pois = len(all_pois_list)

    # --- OBLICZENIA W PAMIĘCI - teraz używamy sprawdzonego kalkulatora ---
    poi_statuses = calculate_poi_statuses(all_pois_list)
    status_counts = Counter(poi_statuses.values())
    stats = {'total': total_pois, 'zdobyty': status_counts.get('zdobyty', 0),
             'do_ponowienia': status_counts.get('do_ponowienia', 0), 'niezdobyty': status_counts.get('niezdobyty', 0),
             'nieaktywny': status_counts.get('nieaktywny', 0), }

    # Tworzymy listę dla szablonu, łącząc POI z jego obliczonym statusem
    pois_with_status = [{'poi': poi, 'status': poi_statuses.get(poi.id, 'nieaktywny')} for poi in all_pois_list]
    sorted_pois = sorted(pois_with_status, key=lambda x: x['poi'].height or 0, reverse=True)

    # ... (reszta logiki: liczenie dla dzieci, mapa, kontekst - bez zmian) ...
    poi_fk_map = {'provinces': 'province_id', 'subprovinces': 'subprovince_id', 'macroregions': 'macroregion_id',
                  'mesoregions': 'mesoregion_id', 'voivodeships': 'voivodeship_id'}
    for relation_name, data in children_data.items():
        poi_fk_field = poi_fk_map.get(relation_name)
        if poi_fk_field:
            counts = Counter(
                getattr(poi, poi_fk_field) for poi in all_pois_list if getattr(poi, poi_fk_field) is not None)
            data['counts'] = counts
    folium_map = None
    if show_map:
        map_kwargs = {'region_object': region_object, 'poi_list': all_pois_list, 'poi_statuses': poi_statuses,
                      'show_pois': show_pois, 'show_heatmap': show_heatmap, 'show_neighbors': show_neighbors, }
        if show_heatmap:
            poi_scores = calculate_scores_for_queryset(all_pois_list)
            map_kwargs['poi_scores'] = poi_scores
        folium_map = create_region_map_with_folium(request=request, **map_kwargs)
    context = {'region': region_object, 'region_type_display': region_object._meta.verbose_name.title(),
               'parent_regions': parent_regions, 'breadcrumbs': breadcrumbs, 'stats': stats,
               'pois_on_page': sorted_pois, 'show_map': show_map, 'show_pois': show_pois, 'show_heatmap': show_heatmap,
               'show_neighbors': show_neighbors, 'folium_map': folium_map._repr_html_() if folium_map else None, }
    subregions_list = []
    for relation_name, data in children_data.items():
        if relation_name != 'voivodeships':
            for child in data['queryset']:
                subregions_list.append({'object': child, 'poi_count': data['counts'].get(child.id, 0),
                                        'url': reverse('odznaki:geography-region-detail',
                                                       kwargs={'model_name': relation_name.rstrip('s'),
                                                               'pk': child.pk})})
    context['subregions'] = sorted(subregions_list, key=lambda x: x['poi_count'], reverse=True)

    return render(request, 'odznaki/geography/region_detail.html', context)


def mountain_range_detail_view(request, range_slug):
    """
    Wersja 2.4: Użycie `POIStatusCalculator` dla 100% spójności statusów.
    """
    if range_slug not in MOUNTAIN_RANGES:
        raise Http404("Nie znaleziono takiego łańcucha górskiego.")

    range_config = MOUNTAIN_RANGES[range_slug]

    # --- Logika agregacji geometrii (bez zmian) ---
    regions_to_union = []
    if range_config.get('province_ids'):
        regions_to_union.extend(
            list(Province.objects.filter(id__in=range_config['province_ids']).exclude(shape__isnull=True)))
    if range_config.get('subprovince_ids'):
        regions_to_union.extend(
            list(SubProvince.objects.filter(id__in=range_config['subprovince_ids']).exclude(shape__isnull=True)))
    if range_config.get('macroregion_ids'):
        regions_to_union.extend(
            list(MacroRegion.objects.filter(id__in=range_config['macroregion_ids']).exclude(shape__isnull=True)))
    aggregated_shape = None
    if regions_to_union:
        try:
            base_geom = regions_to_union[0].shape
            if len(regions_to_union) > 1:
                for i in range(1, len(regions_to_union)):
                    base_geom = base_geom.union(regions_to_union[i].shape.buffer(0))
            aggregated_shape = base_geom
        except GEOSException:
            aggregated_shape = None

    # --- NOWA, UJEDNOLICONA LOGIKA POBIERANIA POI I STATUSÓW ---
    query = Q()
    if range_config.get('province_ids'):
        query |= Q(province_id__in=range_config['province_ids'])
    if range_config.get('subprovince_ids'):
        query |= Q(subprovince_id__in=range_config['subprovince_ids'])
    if range_config.get('macroregion_ids'):
        query |= Q(macroregion_id__in=range_config['macroregion_ids'])

    all_pois_in_region_qs = PointOfInterest.objects.filter(query) if query else PointOfInterest.objects.none()

    # Używamy tej samej logiki prefetch co w `geography_region_detail_view`
    pois_qs_optimized = all_pois_in_region_qs.select_related('mesoregion').defer('mesoregion__shape').prefetch_related(
        'visits',
        Prefetch(
            'badge_requirements',
            queryset=BadgeRequirement.objects.select_related('badge')
        )
    )
    all_pois_list = list(pois_qs_optimized)

    # Używamy naszego sprawdzonego kalkulatora
    poi_statuses = calculate_poi_statuses(all_pois_list)
    # --- KONIEC NOWEJ LOGIKI ---

    # --- Reszta widoku (przetwarzanie i kontekst) jest już poprawna ---
    status_counts = Counter(poi_statuses.values())
    total_pois = len(all_pois_list)
    stats = {'total': total_pois, 'zdobyty': status_counts.get('zdobyty', 0),
             'do_ponowienia': status_counts.get('do_ponowienia', 0), 'niezdobyty': status_counts.get('niezdobyty', 0),
             'nieaktywny': status_counts.get('nieaktywny', 0), }

    pois_with_status = [{'poi': poi, 'status': poi_statuses.get(poi.id, 'nieaktywny')} for poi in all_pois_list]
    sorted_pois = sorted(pois_with_status, key=lambda x: x['poi'].height or 0, reverse=True)

    show_pois = request.GET.get('show_pois', '0') == '1'

    class FakeRegion:
        def __init__(self, name, shape):
            self.name = name;
            self._meta = self;
            self.model_name = 'mountain_range';
            self.shape = shape

    map_kwargs = {
        'region_object': FakeRegion(name=range_config['name'], shape=aggregated_shape),
        'poi_list': all_pois_list,
        'poi_statuses': poi_statuses,  # Przekazujemy słownik statusów
        'poi_scores': calculate_scores_for_queryset(all_pois_list),
        'show_heatmap': True,
        'show_pois': show_pois,
        'show_neighbors': False,
    }
    folium_map = create_region_map_with_folium(request=request, **map_kwargs)

    context = {
        'range_config': range_config, 'stats': stats, 'pois_on_page': sorted_pois,
        'folium_map': folium_map._repr_html_(), 'show_pois': show_pois,
    }

    return render(request, 'odznaki/geography/mountain_range_detail.html', context)


# --- NOWY WIDOK AJAX ---
def get_subregions_json(request, parent_model_name, parent_id):
    """
    Widok AJAX, który zwraca listę podregionów dla danego regionu nadrzędnego.
    """
    children_map = {
        'country': Province,
        'province': SubProvince,
        'subprovince': MacroRegion,
        'macroregion': MesoRegion,
    }

    child_model = children_map.get(parent_model_name)
    if not child_model:
        return JsonResponse({'error': 'Invalid parent model name'}, status=400)

    # Filtrujemy "dzieci" po ID "rodzica"
    subregions = child_model.objects.filter(**{f'{parent_model_name}_id': parent_id}).values('id', 'name')

    return JsonResponse(list(subregions), safe=False)
