# odznaki/views/poi_detail_views.py

from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from odznaki.models import PointOfInterest, Badge, Visit, Trip  # <-- DODAJEMY TRIP
from odznaki.utils.map_utils import create_poi_vicinity_map
from odznaki.services.point_of_interest_service import calculate_poi_statuses
from odznaki.services import scoring_service


def poi_detail_view(request, poi_id):
    """
    Widok wyświetlający szczegółowe informacje o jednym punkcie POI.
    """
    main_poi = get_object_or_404(
        PointOfInterest.objects.select_related('mesoregion').prefetch_related(
            'photos',
            'visits',
            'badge_requirements__badge'
        ),
        id=poi_id
    )

    # --- NOWA, ULEPSZONA LOGIKA DLA WIZYT ---

    # 1. Pobierz wszystkie wizyty dla tego POI
    visits_qs = main_poi.visits.all().order_by('-visit_date')
    visit_dates = [v.visit_date for v in visits_qs]

    # 2. Znajdź wszystkie wycieczki, które odbyły się w te same dni
    trips_by_date = {
        trip.date: trip
        for trip in Trip.objects.filter(date__in=visit_dates)
    }

    # 3. Przygotuj listę wizyt z "doklejonymi" wycieczkami
    visits_with_context = []
    for visit in visits_qs:
        visits_with_context.append({
            'visit': visit,
            'trip': trips_by_date.get(visit.visit_date)  # Pobierz pasującą wycieczkę lub None
        })

    # --- KONIEC NOWEJ LOGIKI ---

    # Logika dla odznak i statusu ogólnego pozostaje bez zmian
    related_badges_with_status = []
    for req in main_poi.badge_requirements.all():
        badge = req.badge
        is_claimed_for_this_badge = False
        for visit_date in visit_dates:
            if (not badge.start_date or visit_date >= badge.start_date) and \
                (not badge.end_date or visit_date <= badge.end_date):
                is_claimed_for_this_badge = True
                break
        related_badges_with_status.append({
            'badge': badge, 'is_claimed': is_claimed_for_this_badge
        })

    #poi_qs_for_status = PointOfInterest.objects.filter(id=main_poi.id)
    poi_qs_for_status = PointOfInterest.objects.filter(id=main_poi.id).prefetch_related(
        'visits',
        'badge_requirements__badge'
    )
    poi_status_dict = calculate_poi_statuses(poi_qs_for_status)
    poi_general_status = poi_status_dict.get(main_poi.id, 'nieaktywny')

    poi_score = scoring_service.get_score_for_single_poi(main_poi)

    folium_map = create_poi_vicinity_map(main_poi, request)

    context = {
        'poi': main_poi,
        'visits_with_context': visits_with_context,  # <-- Przekazujemy nową listę
        'related_badges': related_badges_with_status,
        'general_status': poi_general_status,
        'folium_map': folium_map,  # No need for _repr_html_() here as it's already called in create_poi_vicinity_map
        'poi_score': poi_score,
    }

    return render(request, 'odznaki/poi_detail.html', context)
