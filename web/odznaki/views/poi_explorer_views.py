# odznaki/views/poi_explorer_views.py

import csv
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.db.models import Q, ObjectDoesNotExist, Max
from datetime import date

from odznaki.models import PointOfInterest, Visit, Country, Province, SubProvince, MacroRegion, MesoRegion
from odznaki.services.point_of_interest_service import calculate_poi_statuses

from odznaki.models import PointOfInterest, Country, Province, SubProvince, MacroRegion, MesoRegion

# --- NOWE IMPORTY NASZYCH HELPERÓW ---
from odznaki.utils.poi_explorer_helpers import (
    apply_db_filters,
    apply_annotations,
    apply_ordering,
    prepare_json_data
)


def _get_active_filters(request, available_categories):
    """Funkcja pomocnicza do budowania listy pigułek (bez zmian)."""
    active_filters = []

    name_filter = request.GET.get('name', '')
    if name_filter: active_filters.append({'type': 'name', 'label': 'Nazwa', 'value': name_filter})

    category_filter = request.GET.get('category', '')
    if category_filter:
        label = dict(available_categories).get(category_filter, category_filter)
        active_filters.append({'type': 'category', 'label': 'Kategoria', 'value': label})

    status_filter = request.GET.get('status', '')
    if status_filter:
        status_labels = {'zdobyty': 'Zdobyte', 'do_ponowienia': 'Do ponowienia', 'niezdobyty': 'Do zdobycia',
                         'nieaktywny': 'Nieaktywne'}
        active_filters.append({'type': 'status', 'label': 'Status', 'value': status_labels.get(status_filter)})

    height_from_filter = request.GET.get('height_from', '')
    if height_from_filter: active_filters.append(
        {'type': 'height_from', 'label': 'Wysokość od', 'value': f"{height_from_filter} m"})

    height_to_filter = request.GET.get('height_to', '')
    if height_to_filter: active_filters.append(
        {'type': 'height_to', 'label': 'Wysokość do', 'value': f"{height_to_filter} m"})

    region_filter = request.GET.get('region', '')
    if region_filter:
        try:
            region_type, region_id = region_filter.split(':')
            model_map = {'country': Country, 'province': Province, 'subprovince': SubProvince,
                         'macroregion': MacroRegion, 'mesoregion': MesoRegion}
            model = model_map.get(region_type)
            if model and region_id.isdigit():
                region_name = model.objects.get(pk=int(region_id)).name
                type_label = model._meta.verbose_name.title()
                active_filters.append({'type': 'region', 'label': type_label, 'value': region_name})
        except (ValueError, KeyError, ObjectDoesNotExist):
            pass

    return active_filters


# --- NOWA FUNKCJA DO OBSŁUGI EKSPORTU CSV ---
def handle_csv_export(request):
    """
    Generuje i zwraca plik CSV z przefiltrowanymi punktami POI.
    """
    # KROK 1: Zastosuj te same filtry, co dla tabeli
    queryset = apply_db_filters(request, PointOfInterest.objects.all())
    db_filtered_ids = list(queryset.values_list('id', flat=True))

    poi_for_status_calc = PointOfInterest.objects.filter(id__in=db_filtered_ids).prefetch_related('visits',
                                                                                                  'badge_requirements__badge')
    poi_statuses = calculate_poi_statuses(list(poi_for_status_calc))

    status_filter = request.GET.get('status', '')
    if status_filter:
        final_ids = [pid for pid in db_filtered_ids if poi_statuses.get(pid) == status_filter]
    else:
        final_ids = db_filtered_ids

    # KROK 2: Pobierz PEŁNĄ listę przefiltrowanych obiektów (bez paginacji!)
    results_qs = PointOfInterest.objects.filter(id__in=final_ids).select_related(
        'mesoregion', 'voivodeship'
    ).order_by('name')

    last_visits_qs = Visit.objects.filter(point_of_interest__in=results_qs).values('point_of_interest_id').annotate(
        last_date=Max('visit_date'))
    last_visits = {v['point_of_interest_id']: v['last_date'] for v in last_visits_qs}

    # KROK 3: Przygotuj odpowiedź HTTP
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="poi_export_{date.today().isoformat()}.csv"'},
    )
    response.write('\ufeff'.encode('utf8'))

    # KROK 4: Wygeneruj zawartość CSV
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['ID', 'Nazwa', 'Status', 'Wysokosc', 'Kategoria', 'Mezoregion', 'Wojewodztwo', 'Data ost. wizyty'])

    for poi in results_qs:
        last_visit_date = last_visits.get(poi.id)
        writer.writerow([
            poi.id,
            poi.name,
            poi_statuses.get(poi.id, 'nieaktywny'),
            poi.height or '',
            poi.get_category_display(),
            poi.mesoregion.name if poi.mesoregion else '',
            poi.voivodeship.name if poi.voivodeship else '',
            last_visit_date.strftime('%Y-%m-%d') if last_visit_date else '',
        ])

    return response


def poi_explorer_view(request):
    """
    Wersja 9.0: Ostateczna, niezawodna wersja oparta na POIStatusCalculator.
    """
    if request.GET.get('format') == 'csv':
        return handle_csv_export(request)

    if 'draw' in request.GET:
        # KROK 1: Szybkie filtrowanie w DB
        queryset = apply_db_filters(request, PointOfInterest.objects.all())
        db_filtered_ids = list(queryset.values_list('id', flat=True))
        records_total = PointOfInterest.objects.count()

        # KROK 2: Oblicz statusy TYLKO dla przefiltrowanych POI
        poi_for_status_calc = PointOfInterest.objects.filter(id__in=db_filtered_ids).prefetch_related('visits',
                                                                                                      'badge_requirements__badge')
        poi_statuses = calculate_poi_statuses(list(poi_for_status_calc))

        # KROK 3: Zastosuj filtr statusu w Pythonie
        status_filter = request.GET.get('status', '')
        if status_filter:
            final_ids = [pid for pid in db_filtered_ids if poi_statuses.get(pid) == status_filter]
        else:
            final_ids = db_filtered_ids
        records_filtered = len(final_ids)

        # KROK 4: Sortowanie i Paginacja (uproszczone dla niezawodności)
        # TODO: W przyszłości można zaimplementować pełne sortowanie w Pythonie
        final_qs = PointOfInterest.objects.filter(id__in=final_ids).order_by('name')

        start = int(request.GET.get('start', 0));
        length = int(request.GET.get('length', 10))
        paginated_poi_list = list(final_qs.select_related('mesoregion', 'voivodeship')[start:start + length])

        # KROK 5: Dociągnij ostatnie wizyty i sformatuj JSON
        last_visits_qs = Visit.objects.filter(point_of_interest__in=paginated_poi_list).values(
            'point_of_interest_id').annotate(last_date=Max('visit_date'))
        last_visits = {v['point_of_interest_id']: v['last_date'] for v in last_visits_qs}

        json_data = prepare_json_data(paginated_poi_list, poi_statuses, last_visits)

        return JsonResponse({
            'draw': int(request.GET.get('draw', '1')),
            'recordsTotal': records_total, 'recordsFiltered': records_filtered, 'data': json_data
        })

    # --- Obsługa zwykłego ładowania strony (GET) ---
    available_categories = PointOfInterest.Category.choices
    available_countries = Country.objects.all().order_by('name')
    active_filters = _get_active_filters(request, available_categories)

    context = {'available_categories': available_categories,
               'available_countries': available_countries,
               'current_filters': request.GET,
               'active_filters': active_filters}
    return render(request, 'odznaki/poi_explorer.html', context)