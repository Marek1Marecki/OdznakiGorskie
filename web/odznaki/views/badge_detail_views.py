# odznaki/views/badges.py (lub inny plik w pakiecie views)

from django.shortcuts import render, get_object_or_404

from odznaki.models import Badge, Visit, BadgeLevel, Trip
from odznaki.utils.map_utils import create_badge_map_with_folium

def badge_detail_view(request, badge_id):
    """
    Widok wyświetlający szczegółowe informacje o jednej odznace,
    wraz z mapą i listą punktów POI.
    """
    badge = get_object_or_404(
        Badge.objects.prefetch_related(
            'points_of_interest',
            'levels' # <-- NOWOŚĆ: Pobieramy od razu wszystkie stopnie odznaki
        ),
        id=badge_id
    )

    poi_ids_in_badge = badge.points_of_interest.values_list('id', flat=True)
    relevant_visits = Visit.objects.filter(point_of_interest_id__in=poi_ids_in_badge)

    # --- NOWA, ULEPSZONA LOGIKA ---
    # 1. Stwórz mapę dat wizyt do powiązanych z nimi wycieczek
    visit_dates_with_trips = {}
    for trip in Trip.objects.filter(date__in=[v.visit_date for v in relevant_visits]):
        visit_dates_with_trips[trip.date] = trip.id

    # 2. Zbuduj słownik z danymi o wizytach, uwzględniając ID wycieczki
    visited_poi_data = {}
    for visit in relevant_visits:
        is_after_start = not badge.start_date or visit.visit_date >= badge.start_date
        is_before_end = not badge.end_date or visit.visit_date <= badge.end_date

        if is_after_start and is_before_end:
            if visit.point_of_interest_id not in visited_poi_data:
                visited_poi_data[visit.point_of_interest_id] = []

            visited_poi_data[visit.point_of_interest_id].append({
                'date': visit.visit_date,
                'trip_id': visit_dates_with_trips.get(visit.visit_date)  # Pobierz ID wycieczki lub None
            })

    visited_poi_ids = set(visited_poi_data.keys())

    # --- Przygotowanie danych dla szablonu ---
 
    # 3. Oblicz postęp (możemy użyć istniejącego serwisu lub prostej logiki)
    progress_data = {
        'achieved_count': len(visited_poi_ids),
        'required_count': badge.required_poi_count,
        'percentage': min(100.0, (len(visited_poi_ids) / badge.required_poi_count) * 100.0) if badge.required_poi_count > 0 else 0
    }

    # --- NOWA LOGIKA: Obliczanie postępu dla każdego stopnia ---
    levels_with_progress = []
    # Wykorzystujemy już pobrane `badge.levels.all()` dzięki prefetch_related
    for level in badge.levels.all():
        # Tutaj logika jest uproszczona - zakładamy, że postęp do stopnia jest
        # równy ogólnemu postępowi w zdobywaniu punktów dla odznaki.
        # W przyszłości można by to rozbudować o bardziej złożone zasady.

        required = level.poi_count
        achieved = len(visited_poi_ids)

        # Ograniczamy "zdobyte" do "wymaganych", aby progressbar nie przekroczył 100%
        # np. dla stopnia brązowego (15 POI), nawet jeśli mamy 20, pokazujemy 15.
        achieved_for_level = min(achieved, required)

        percentage = (achieved_for_level / required) * 100 if required > 0 else 0

        levels_with_progress.append({
            'level': level,
            'achieved_count': achieved_for_level,
            'required_count': required,
            'percentage': percentage,
        })

    # Wywołanie funkcji - przekazujemy argumenty przez kwargs
    badge_map_html = create_badge_map_with_folium(badge, visited_poi_ids, request)

    context = {
        'badge': badge,
        'visited_poi_data': visited_poi_data,
        'progress_data': progress_data,
        'levels_with_progress': levels_with_progress,
        'folium_map': badge_map_html,
    }

    return render(request, 'odznaki/badge_detail.html', context)