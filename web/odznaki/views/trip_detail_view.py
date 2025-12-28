# odznaki/views/trip_detail_view.py

from django.shortcuts import render, get_object_or_404
from django.contrib.gis.geos import LineString
from django.contrib.gis.db.models.functions import Transform

from odznaki.models import Trip, PointOfInterest, Visit
from odznaki.services import trip_service
from odznaki.utils.map_utils import create_trip_map_with_folium


def trip_detail_view(request, trip_id):
    """
    Widok wyświetlający szczegóły jednej wycieczki.
    """
    trip = get_object_or_404(Trip.objects.prefetch_related('gpx_paths'), id=trip_id)

    # ... (istniejąca logika dla `full_trip_linestring` i `discovered_pois` bez zmian) ...
    all_segments_coords = []
    for segment in trip.gpx_paths.order_by('sequence'):
        if segment.gpx_path:
            all_segments_coords.extend(segment.gpx_path.coords)
    full_trip_linestring = LineString(all_segments_coords, srid=4326) if all_segments_coords else None

    nearby_pois_qs = PointOfInterest.objects.none()
    if full_trip_linestring:
        trip_path_metric = full_trip_linestring.transform(3857, clone=True)
        nearby_pois_qs = PointOfInterest.objects.annotate(
            location_metric=Transform('location', 3857)
        ).filter(
            location_metric__dwithin=(trip_path_metric, 100)
        ).order_by('name')

    discovered_pois_with_status = []
    if nearby_pois_qs.exists() and trip.date:
        visited_poi_ids_on_date = set(Visit.objects.filter(
            point_of_interest__in=nearby_pois_qs,
            visit_date=trip.date
        ).values_list('point_of_interest_id', flat=True))
        for poi in nearby_pois_qs:
            discovered_pois_with_status.append({'poi': poi, 'is_visited': poi.id in visited_poi_ids_on_date})

    folium_map = create_trip_map_with_folium(trip, nearby_pois_qs, request)
    mesoregions_on_route = trip_service.find_mesoregions_for_trip(trip)

    # --- NOWA LINIA: POBIERAMY DANE DLA WYKRESU ---
    elevation_profile_data = trip_service.get_elevation_profile_data(trip)

    context = {
        'trip': trip,
        'discovered_pois': discovered_pois_with_status,
        'folium_map': folium_map,
        'mesoregions_on_route': mesoregions_on_route,
        'elevation_profile_data': elevation_profile_data,  # <-- Przekazujemy dane do szablonu
    }

    return render(request, 'odznaki/trips/trip_detail.html', context)