# odznaki/views/trip_list_view.py

import csv
from datetime import date
from django.http import HttpResponse # <-- DODAJ TĘ LINIĘ

from django.shortcuts import render
from django.db.models import Q, ObjectDoesNotExist
from odznaki.models import Trip, MesoRegion, TripSegment, PointOfInterest
from odznaki.services import trip_service


def handle_trip_csv_export(request):
    """
    Generuje i zwraca plik CSV z przefiltrowaną listą wycieczek.
    """
    # KROK 1: Ponownie wykorzystaj logikę filtrowania z głównego widoku
    year_param = request.GET.get('year', 'all')
    year_filter = int(year_param) if year_param.isdigit() else None
    mesoregion_param = request.GET.get('mesoregion', 'all')
    mesoregion_id = int(mesoregion_param) if mesoregion_param.isdigit() else None
    search_query = request.GET.get('search', '').strip()

    trips_qs = Trip.objects.all()  # Zaczynamy od wszystkich
    if year_filter: trips_qs = trips_qs.filter(date__year=year_filter)
    if search_query: trips_qs = trips_qs.filter(
        Q(start_point_name__icontains=search_query) | Q(end_point_name__icontains=search_query) | Q(
            description__icontains=search_query))
    if mesoregion_id:
        try:
            selected_region = MesoRegion.objects.get(pk=mesoregion_id)
            trip_ids_in_region = TripSegment.objects.filter(gpx_path__intersects=selected_region.shape).values_list(
                'trip_id', flat=True).distinct()
            trips_qs = trips_qs.filter(id__in=trip_ids_in_region)
        except (MesoRegion.DoesNotExist, ValueError):
            pass

    # Sortujemy, aby eksport był uporządkowany (np. chronologicznie)
    results_qs = trips_qs.order_by('-date')

    # KROK 2: Przygotuj odpowiedź HTTP
    response = HttpResponse(content_type='text/csv', headers={
        'Content-Disposition': f'attachment; filename="trips_export_{date.today().isoformat()}.csv"'})
    response.write('\ufeff'.encode('utf8'))

    # KROK 3: Wygeneruj zawartość CSV
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Data', 'Trasa', 'Dystans (km)', 'Suma Podejsc (m)', 'Punkty GOT', 'Everest (m)', 'Regiony'])

    for trip in results_qs:
        # Znajdź regiony dla każdej wycieczki (ta logika jest już w głównym widoku)
        mesoregions = trip_service.find_mesoregions_for_trip(trip)
        region_names = ", ".join([r.name for r in mesoregions])

        writer.writerow([
            trip.date,
            str(trip),
            trip.total_distance_km,
            trip.total_elevation_gain_m,
            trip.got_points,
            trip.everest_diff_m,
            region_names
        ])

    return response


def trip_list_view(request):
    """
    Wersja 2.0: Z dodaną logiką dla pigułek aktywnych filtrów.
    """
    # --- NOWY BLOK: Sprawdź, czy żądanie dotyczy eksportu CSV ---
    if request.GET.get('format') == 'csv':
        return handle_trip_csv_export(request)

    # --- Pobieranie opcji dla filtrów ---
    available_years = Trip.objects.filter(date__isnull=False).dates('date', 'year', order='DESC')

    # Krok 1: Znajdź ID wszystkich mezoregionów, używając `related_query_name`.
    mesoregion_ids = PointOfInterest.objects.filter(
        mesoregion__isnull=False,
        badge_requirement__isnull=False # <-- UŻYWAMY `badge_requirement`
    ).values_list('mesoregion_id', flat=True).distinct()

    # Krok 2: Pobierz obiekty MesoRegion (bez zmian)
    available_mesoregions = MesoRegion.objects.filter(
        id__in=mesoregion_ids
    ).values_list('id', 'name').order_by('name')

    # --- Pobieranie i walidacja parametrów ---
    year_param = request.GET.get('year', 'all')
    year_filter = int(year_param) if year_param.isdigit() else None
    mesoregion_param = request.GET.get('mesoregion', 'all')
    mesoregion_id = int(mesoregion_param) if mesoregion_param.isdigit() else None
    search_query = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'date_desc')

    # --- Budowanie QuerySetu ---
    trips_qs = Trip.objects.prefetch_related('gpx_paths').all()
    if year_filter:
        trips_qs = trips_qs.filter(date__year=year_filter)
    if search_query:
        trips_qs = trips_qs.filter(
            Q(start_point_name__icontains=search_query) | Q(end_point_name__icontains=search_query) | Q(
                description__icontains=search_query))
    if mesoregion_id:
        try:
            selected_region = MesoRegion.objects.get(pk=mesoregion_id)
            trip_ids_in_region = TripSegment.objects.filter(gpx_path__intersects=selected_region.shape).values_list(
                'trip_id', flat=True).distinct()
            trips_qs = trips_qs.filter(id__in=trip_ids_in_region)
        except (MesoRegion.DoesNotExist, ValueError):
            pass

    # --- Sortowanie ---
    sort_mapping = {'date_desc': '-date', 'date_asc': 'date', 'distance_desc': '-total_distance_km',
                    'distance_asc': 'total_distance_km', 'got_desc': '-got_points', 'got_asc': 'got_points', }
    order_field = sort_mapping.get(sort_by, '-date')
    trips_qs = trips_qs.order_by(order_field)

    # --- Wzbogacanie danych ---
    trips_with_context = []
    for trip in trips_qs:
        mesoregions = trip_service.find_mesoregions_for_trip(trip)
        trips_with_context.append({'trip': trip, 'mesoregions': mesoregions})

    # --- Budowanie listy pigułek ---
    active_filters = []
    if search_query:
        active_filters.append({'type': 'search', 'label': 'Fraza', 'value': search_query})
    if year_filter:
        active_filters.append({'type': 'year', 'label': 'Rok', 'value': year_filter})
    if mesoregion_id:
        try:
            region_name = MesoRegion.objects.get(pk=mesoregion_id).name
            active_filters.append({'type': 'mesoregion', 'label': 'Mezoregion', 'value': region_name})
        except ObjectDoesNotExist:
            pass

    # --- Przygotowanie finalnego kontekstu ---
    context = {
        'trips_list_with_context': trips_with_context,
        'available_years': available_years,
        'available_mesoregions': available_mesoregions,
        'current_filters': {
            'year': year_filter or 'all',
            'mesoregion': mesoregion_id or 'all',
            'search': search_query,
            'sort': sort_by,
        },
        'active_filters': active_filters,
    }
    return render(request, 'odznaki/trips/trip_list.html', context)