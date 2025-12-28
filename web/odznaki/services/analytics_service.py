# odznaki/services/analytics_service.py
import logging
import math
from collections import defaultdict, Counter
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.fields import LineStringField
from geopy.distance import geodesic
from django.db.models import Sum, Count
from django.db.models.functions import ExtractYear
from django.db.models import F, Func
from django.db import connection

# Importujemy modele, których będziemy używać
from odznaki.models import Trip, TripSegment, MesoRegion, Visit, BadgeLevel, PointOfInterest

logger = logging.getLogger(__name__)





def calculate_activity_by_mesoregion():
    logger.info("Rozpoczynam PRECYZYJNE obliczanie aktywności w mezoregionach (metoda ETL)...")

    all_regions = list(MesoRegion.objects.exclude(shape__isnull=True))
    all_trips = Trip.objects.prefetch_related('gpx_paths').all()
    results = defaultdict(lambda: {'mesoregion': None, 'total_distance_m': 0.0, 'total_elevation_gain_m': 0.0})

    for trip in all_trips:
        points_3d = []
        for segment in trip.gpx_paths.order_by('sequence'):
            if segment.gpx_path:
                points_3d.extend(segment.gpx_path.coords)
        if len(points_3d) < 2: continue

        enriched_points = []
        for i, p_coords in enumerate(points_3d):
            current_point_geom = Point(p_coords[0], p_coords[1], srid=4326)

            found_region = next((r for r in all_regions if r.shape.contains(current_point_geom)), None)

            distance_to_next = 0
            elevation_diff = 0

            if i < len(points_3d) - 1:
                next_p_coords = points_3d[i + 1]
                next_point_geom = Point(next_p_coords[0], next_p_coords[1], srid=4326)

                coords1 = (current_point_geom.y, current_point_geom.x)
                coords2 = (next_point_geom.y, next_point_geom.x)
                distance_to_next = geodesic(coords1, coords2).meters
                logger.debug(f"Obliczona odległość między {coords1} a {coords2}: {distance_to_next} m")

                if len(p_coords) > 2 and len(next_p_coords) > 2 and p_coords[2] is not None and next_p_coords[2] is not None:
                    elevation_diff = next_p_coords[2] - p_coords[2]

            enriched_points.append({
                'region': found_region, 'distance_m': distance_to_next, 'elevation_gain_m': max(0, elevation_diff)
            })

        for point_data in enriched_points:
            if point_data['region']:
                region_id = point_data['region'].id
                results[region_id]['mesoregion'] = point_data['region']
                results[region_id]['total_distance_m'] += point_data['distance_m']
                results[region_id]['total_elevation_gain_m'] += point_data['elevation_gain_m']

    final_results = []
    for region_id, data in results.items():
        dist_km = data['total_distance_m'] / 1000
        elev_m = data['total_elevation_gain_m']
        final_results.append({
            'mesoregion': data['mesoregion'],
            'total_distance_km': round(dist_km, 2),
            'total_elevation_gain_m': round(elev_m),
            'total_got_points': math.floor(dist_km) + math.floor(elev_m / 100)
        })

    logger.info(f"Zakończono agregację. Znaleziono aktywność w {len(final_results)} mezoregionach.")
    return sorted(final_results, key=lambda x: x['total_distance_km'], reverse=True)


# --- NOWA FUNKCJA DLA STATYSTYK ROCZNYCH ---
def get_yearly_stats():
    """
    Oblicza i agreguje szczegółowe statystyki aktywności dla każdego roku,
    w którym zanotowano jakąkolwiek aktywność.
    """
    logger.info("Rozpoczynam obliczanie statystyk rocznych...")

    stats_by_year = defaultdict(lambda: {
        'trip_count': 0, 'total_distance_km': 0.0, 'total_elevation_gain_m': 0,
        'total_got_points': 0, 'total_everest_m': 0, 'new_pois_count': 0,
        'badges_earned_count': 0, 'visited_mesoregions_ids': set(),
    })

    # --- 1. Agregacja danych z wycieczek ---
    trips_data = Trip.objects.filter(date__isnull=False).annotate(
        year=ExtractYear('date')
    ).values('year').annotate(
        count=Count('id'), dist=Sum('total_distance_km'),
        elev=Sum('total_elevation_gain_m'), got=Sum('got_points'),
        everest=Sum('everest_diff_m')
    )
    years_with_activity = set()
    for item in trips_data:
        year = item['year']
        years_with_activity.add(year)
        entry = stats_by_year[year]
        entry['trip_count'] = item['count']
        entry['total_distance_km'] = float(item['dist'] or 0)
        entry['total_elevation_gain_m'] = item['elev'] or 0
        entry['total_got_points'] = item['got'] or 0
        entry['total_everest_m'] = item['everest'] or 0

    # --- 2. Agregacja nowo zdobytych POI ---
    all_visits = Visit.objects.values('point_of_interest_id', 'visit_date').order_by('visit_date')
    poi_first_visit_year = {}
    for visit in all_visits:
        poi_id = visit['point_of_interest_id']
        visit_year = visit['visit_date'].year
        if poi_id not in poi_first_visit_year:
            poi_first_visit_year[poi_id] = visit_year
            stats_by_year[visit_year]['new_pois_count'] += 1
            years_with_activity.add(visit_year)

    # --- 3. Agregacja zdobytych odznak ---
    badges_data = BadgeLevel.objects.filter(verified_at__isnull=False).annotate(
        year=ExtractYear('verified_at')
    ).values('year').annotate(count=Count('id'))
    for item in badges_data:
        year = item['year']
        stats_by_year[year]['badges_earned_count'] = item['count']
        years_with_activity.add(year)

    # --- 4. Agregacja odwiedzonych Mezoregionów ---
    visits_with_regions = Visit.objects.filter(
        point_of_interest__mesoregion__isnull=False
    ).annotate(
        year=ExtractYear('visit_date')
    ).values_list('year', 'point_of_interest__mesoregion_id').distinct()
    for year, mesoregion_id in visits_with_regions:
        if year: # Upewniamy się, że rok nie jest None
            stats_by_year[year]['visited_mesoregions_ids'].add(mesoregion_id)

    # --- 5. Formatowanie wyniku ---
    final_list = []
    for year in sorted(list(years_with_activity), reverse=True):
        data = stats_by_year[year]
        final_list.append({
            'year': year,
            'trip_count': data['trip_count'],
            'total_distance_km': round(data['total_distance_km'], 2),
            'total_elevation_gain_m': data['total_elevation_gain_m'],
            'total_got_points': data['total_got_points'],
            'total_everest_m': data['total_everest_m'],
            'new_pois_count': data['new_pois_count'],
            'badges_earned_count': data['badges_earned_count'],
            'visited_mesoregions_count': len(data['visited_mesoregions_ids']),
        })

    logger.info(f"Zakończono. Zebrano statystyki dla {len(final_list)} lat.")
    return final_list


# --- NOWA FUNKCJA DLA MAPY ŚLADÓW GPX ---
def get_gpx_heatmap_data(segment_length_m=20):
    """
    Wersja 2.1: Przygotowuje dane dla mapy cieplnej, używając "surowego" SQL
    do wykonania segmentacji, aby obejść problemy z ORM.
    """
    logger.info(f"Rozpoczynam agregację danych GPX dla mapy cieplnej (segmentacja co {segment_length_m}m)...")

    heatmap_data = []

    # Ponieważ zagnieżdżanie funkcji GIS w Django ORM bywa problematyczne w różnych wersjach,
    # użyjemy "surowego" zapytania SQL, które jest najbardziej niezawodne i wydajne.

    query = """
    SELECT
        ST_Y(geom_4326), -- Szerokość geograficzna (latitude)
        ST_X(geom_4326)  -- Długość geograficzna (longitude)
    FROM (
        SELECT
            ST_Transform(
                (ST_DumpPoints(
                    ST_Segmentize(
                        ST_Transform(gpx_path, 2180), -- Transformuj do układu metrycznego (Polska)
                        %s
                    )
                )).geom,
                4326 -- Transformuj punkty z powrotem do WGS84
            ) as geom_4326
        FROM
            odznaki_trip_segment
        WHERE
            gpx_path IS NOT NULL
    ) AS subquery;
    """

    try:
        with connection.cursor() as cursor:
            # Wykonujemy surowe zapytanie, bezpiecznie przekazując parametr
            cursor.execute(query, [segment_length_m])
            # Pobieramy wszystkie wyniki
            for row in cursor.fetchall():
                heatmap_data.append([row[0], row[1]])
    except Exception as e:
        logger.error(f"Błąd podczas wykonywania surowego zapytania SQL dla heatmapy GPX: {e}")
        return []  # Zwróć pustą listę w razie błędu

    logger.info(f"Zakończono. Zebrano {len(heatmap_data)} równomiernie rozmieszczonych punktów z tras GPX.")
    return heatmap_data


TOP_N_RECORDS = 5
CHART_MAX_SLICES = 9 # Pokaż 9 największych + 1 "Inne"


def get_personal_records():
    """
    Wersja 5.0: Przygotowuje wszystkie dane dla w pełni dynamicznego "Profilu Zdobywcy".
    """
    records = {
        'top_n_value': TOP_N_RECORDS  # Przekazujemy wartość stałej do kontekstu
    }

    # --- 1. REKORDY (bez zmian, dodany rekord GOT) ---
    records['longest_trip_by_dist'] = Trip.objects.order_by('-total_distance_km').first()
    records['trip_with_most_elevation'] = Trip.objects.order_by('-total_elevation_gain_m').first()
    records['trip_with_biggest_everest'] = Trip.objects.order_by('-everest_diff_m').first()
    records['trip_with_most_got'] = Trip.objects.order_by('-got_points').first()
    most_prolific_day_data = Visit.objects.values('visit_date').annotate(
        poi_count=Count('point_of_interest_id', distinct=True)
    ).order_by('-poi_count').first()
    records['most_prolific_day'] = most_prolific_day_data

    # --- 2. PRZYGOTOWANIE DANYCH ŹRÓDŁOWYCH ---

    # Lista wszystkich unikalnych wizyt z pełną hierarchią geograficzną
    visits_with_geo = Visit.objects.select_related(
        'point_of_interest__province',
        'point_of_interest__subprovince',
        'point_of_interest__macroregion',
        'point_of_interest__mesoregion'
    ).order_by('point_of_interest_id', 'visit_date').distinct('point_of_interest_id')

    # Lista wszystkich unikalnych wycieczek, które przeszły przez dany region
    # To jest złożone. Użyjemy prostszej logiki: wycieczka należy do regionu, jeśli choć jedna wizyta z daty tej wycieczki była w tym regionie.
    all_trips_dates = {t.date: t.id for t in Trip.objects.filter(date__isnull=False)}
    visits_on_trip_days = Visit.objects.filter(visit_date__in=all_trips_dates.keys()).select_related(
        'point_of_interest__province', 'point_of_interest__subprovince',
        'point_of_interest__macroregion', 'point_of_interest__mesoregion'
    )

    # --- 3. INICJALIZACJA STRUKTUR DANYCH ---

    # Słowniki do zliczania (dla obu metryk)
    poi_counts = {'province': Counter(), 'subprovince': Counter(), 'macroregion': Counter(), 'mesoregion': Counter()}
    trip_counts = {'province': defaultdict(set), 'subprovince': defaultdict(set), 'macroregion': defaultdict(set),
                   'mesoregion': defaultdict(set)}

    # --- 4. PRZETWARZANIE DANYCH (AGREGACJA W PYTHONIE) ---

    # Agregacja "wg POI"
    for visit in visits_with_geo:
        poi = visit.point_of_interest
        if poi.province: poi_counts['province'][(poi.province.id, poi.province.name)] += 1
        if poi.subprovince: poi_counts['subprovince'][(poi.subprovince.id, poi.subprovince.name)] += 1
        if poi.macroregion: poi_counts['macroregion'][(poi.macroregion.id, poi.macroregion.name)] += 1
        if poi.mesoregion: poi_counts['mesoregion'][(poi.mesoregion.id, poi.mesoregion.name)] += 1

    # Agregacja "wg Wycieczek"
    for visit in visits_on_trip_days:
        trip_id = all_trips_dates.get(visit.visit_date)
        if not trip_id: continue
        poi = visit.point_of_interest
        if poi.province: trip_counts['province'][(poi.province.id, poi.province.name)].add(trip_id)
        if poi.subprovince: trip_counts['subprovince'][(poi.subprovince.id, poi.subprovince.name)].add(trip_id)
        if poi.macroregion: trip_counts['macroregion'][(poi.macroregion.id, poi.macroregion.name)].add(trip_id)
        if poi.mesoregion: trip_counts['mesoregion'][(poi.mesoregion.id, poi.mesoregion.name)].add(trip_id)

    # --- 5. FORMATOWANIE WYNIKÓW ---

    records['top_lists_by_poi'] = {}
    records['chart_data_by_poi'] = {}
    records['top_lists_by_trip'] = {}
    records['chart_data_by_trip'] = {}

    for level in ['province', 'subprovince', 'macroregion', 'mesoregion']:
        # --- Przetwarzanie "wg POI" ---
        sorted_by_poi = sorted(poi_counts[level].items(), key=lambda item: item[1], reverse=True)

        # Logika dla listy Top N (bez zmian)
        records['top_lists_by_poi'][level] = [{'id': region_id, 'name': name, 'count': count} for
                                              (region_id, name), count in sorted_by_poi[:TOP_N_RECORDS]]

        # NOWA LOGIKA DLA WYKRESU:
        chart_labels_poi = [name for (region_id, name), count in sorted_by_poi[:CHART_MAX_SLICES]]
        chart_data_poi = [count for (region_id, name), count in sorted_by_poi[:CHART_MAX_SLICES]]
        # Jeśli jest więcej danych niż limit, dodaj kategorię "Inne"
        if len(sorted_by_poi) > CHART_MAX_SLICES:
            other_sum = sum(count for (region_id, name), count in sorted_by_poi[CHART_MAX_SLICES:])
            chart_labels_poi.append('Inne')
            chart_data_poi.append(other_sum)

        records['chart_data_by_poi'][level] = {'labels': chart_labels_poi, 'data': chart_data_poi}

        # --- Przetwarzanie "wg Wycieczek" ---
        final_trip_counts = {region_tuple: len(trip_ids) for region_tuple, trip_ids in trip_counts[level].items()}
        sorted_by_trip = sorted(final_trip_counts.items(), key=lambda item: item[1], reverse=True)

        # Logika dla listy Top N (bez zmian)
        records['top_lists_by_trip'][level] = [{'id': region_id, 'name': name, 'count': count} for
                                               (region_id, name), count in sorted_by_trip[:TOP_N_RECORDS]]

        # NOWA LOGIKA DLA WYKRESU:
        chart_labels_trip = [name for (region_id, name), count in sorted_by_trip[:CHART_MAX_SLICES]]
        chart_data_trip = [count for (region_id, name), count in sorted_by_trip[:CHART_MAX_SLICES]]
        if len(sorted_by_trip) > CHART_MAX_SLICES:
            other_sum = sum(count for (region_id, name), count in sorted_by_trip[CHART_MAX_SLICES:])
            chart_labels_trip.append('Inne')
            chart_data_trip.append(other_sum)

        records['chart_data_by_trip'][level] = {'labels': chart_labels_trip, 'data': chart_data_trip}

    return records