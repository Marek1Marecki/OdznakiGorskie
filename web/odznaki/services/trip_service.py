"""
Moduł zawierający logikę biznesową związaną z wycieczkami i ścieżkami GPX.
"""
from typing import Dict, Any, Optional, List
from django.db import models, transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.contrib.gis.geos import LineString, Point
from django.contrib.gis.db.models.functions import Transform

from odznaki.models import Trip, TripSegment, MesoRegion
from odznaki.exceptions import ValidationError, BusinessLogicError

import gpxpy
import gpxpy.gpx
import math

import logging


# Ustawienie loggera do śledzenia postępów i ewentualnych błędów
logger = logging.getLogger(__name__)


def parse_gpx_to_linestring_and_stats(gpx_file):
    """
    Parsuje wgrany plik GPX, tworzy z niego obiekt LineString
    i oblicza podstawowe statystyki geograficzne.

    Args:
        gpx_file: Obiekt pliku (InMemoryUploadedFile lub podobny z Django).

    Returns:
        tuple: (LineString, dict) - Krotka zawierająca geometrię LineString
               oraz słownik ze statystykami.

    Raises:
        ValueError: Jeśli plik GPX jest niepoprawny lub zawiera mniej niż 2 punkty.
    """
    try:
        # Upewniamy się, że odczytujemy plik od początku
        gpx_file.seek(0)
        # Dekodujemy zawartość pliku na string, aby gpxpy mogło go sparsować
        gpx_content = gpx_file.read().decode('utf-8')
        gpx = gpxpy.parse(gpx_content)

        points = []
        # Iterujemy przez wszystkie ścieżki i segmenty w pliku GPX
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    # Tworzymy krotki w formacie (długość, szerokość, wysokość)
                    # LineString z GeoDjango oczekuje takiej kolejności.
                    points.append((point.longitude, point.latitude, point.elevation or 0))

        # Sprawdzamy, czy mamy wystarczającą liczbę punktów do stworzenia linii
        if len(points) < 2:
            raise ValueError("Plik GPX musi zawierać co najmniej 2 punkty, aby utworzyć trasę.")

        # Tworzymy obiekt LineString z GeoDjango z SRID=4326 (WGS84)
        linestring = LineString(points, srid=4326)

        # Obliczamy statystyki za pomocą wbudowanych metod gpxpy
        stats = {}

        # Dystans 3D (uwzględniający wysokość) w metrach
        length_3d_meters = gpx.length_3d()
        if length_3d_meters:
            # Konwertujemy na kilometry i zaokrąglamy
            stats['distance_km'] = round(length_3d_meters / 1000, 2)

        # Suma podejść i zejść w metrach
        uphill, downhill = gpx.get_uphill_downhill()
        if uphill:
            # Zaokrąglamy do pełnych metrów
            stats['elevation_gain_m'] = round(uphill)

        logger.info(
            f"Pomyślnie sparsowano plik GPX. Długość: {stats.get('distance_km')} km, Przewyższenie: {stats.get('elevation_gain_m')} m.")

        return linestring, stats

    except gpxpy.gpx.GPXXMLSyntaxException as e:
        logger.error(f"Błąd składni XML w pliku GPX: {e}")
        raise ValueError(f"Błąd w strukturze pliku GPX: {e}")
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd podczas parsowania pliku GPX: {e}")
        # Rzucamy wyjątek dalej, aby model (lub inna logika) mógł go obsłużyć
        raise


def get_segment_stats(segment):
    """
    Oblicza statystyki (dystans, przewyższenie) dla pojedynczego segmentu trasy.
    Używa do tego sparsowanego obiektu GPX, jeśli jest dostępny,
    lub geometrii LineString.
    """
    stats = {
        'distance_km': 0,
        'elevation_gain_m': 0
    }
    # Użycie gpxpy do precyzyjnych obliczeń, jeśli plik jest dostępny
    if segment.gpx_file:
        try:
            segment.gpx_file.seek(0)
            gpx_content = segment.gpx_file.read().decode('utf-8')
            gpx = gpxpy.parse(gpx_content)

            length_3d = gpx.length_3d()
            if length_3d:
                stats['distance_km'] = round(length_3d / 1000, 2)

            uphill, _ = gpx.get_uphill_downhill()
            if uphill:
                stats['elevation_gain_m'] = round(uphill)

            return stats
        except Exception:
            # Jeśli parsowanie zawiedzie, przejdź do metody awaryjnej
            pass

    # Metoda awaryjna: obliczenia na podstawie geometrii LineString
    if segment.gpx_path:
        try:
            # Transformujemy całą ścieżkę do układu metrycznego, aby uzyskać długość w metrach
            path_metric = segment.gpx_path.transform(3857, clone=True)
            stats['distance_km'] = round(path_metric.length / 1000, 2)
        except Exception:
            # Jeśli transformacja się nie powiedzie, wracamy do zera
            stats['distance_km'] = 0

        # Obliczanie przewyższenia z geometrii (ta logika jest już poprawna)
        points = segment.gpx_path.coords
        elevation_gain = 0
        for i in range(len(points) - 1):
            if len(points[i]) > 2 and len(points[i + 1]) > 2:
                diff = points[i + 1][2] - points[i][2]
                if diff > 0:
                    elevation_gain += diff
        stats['elevation_gain_m'] = round(elevation_gain)

    return stats


def recalculate_trip_stats(trip: Trip):
    """
    Oblicza wszystkie statystyki dla danej wycieczki i aktualizuje jej pola.
    Zawiera poprawny algorytm obliczania "Everestu".
    """
    total_distance = 0
    total_elevation = 0
    all_points_in_order = []

    for segment in trip.gpx_paths.order_by('sequence'):
        stats = get_segment_stats(segment)
        total_distance += stats.get('distance_km', 0)
        total_elevation += stats.get('elevation_gain_m', 0)
        if segment.gpx_path:
            all_points_in_order.extend(segment.gpx_path.coords)

    # --- NOWA, POPRAWNA LOGIKA OBLICZANIA "EVEREST" (Wersja 4.0) ---
    everest_diff = 0
    if len(all_points_in_order) > 1:
        # Wyciągamy samą listę wysokości dla czytelności
        elevations = [p[2] for p in all_points_in_order]

        max_everest_diff = 0
        # Najniższy punkt znaleziony do tej pory to wysokość startowa
        min_elevation_so_far = elevations[0]

        # Iterujemy po trasie od drugiego punktu
        for i in range(1, len(elevations)):
            current_elevation = elevations[i]

            # Oblicz potencjalny zysk wysokości od najniższego punktu do teraz
            potential_diff = current_elevation - min_elevation_so_far

            # Zaktualizuj maksymalny zysk, jeśli obecny jest większy
            max_everest_diff = max(max_everest_diff, potential_diff)

            # Zaktualizuj najniższy punkt znaleziony do tej pory
            min_elevation_so_far = min(min_elevation_so_far, current_elevation)

        everest_diff = max_everest_diff
    # --- KONIEC NOWEJ LOGIKI ---

    # Aktualizujemy pola modelu
    trip.total_distance_km = round(total_distance, 2)
    trip.total_elevation_gain_m = round(total_elevation)
    trip.got_points = math.floor(total_distance) + math.floor(total_elevation / 100)
    trip.everest_diff_m = round(everest_diff)

    # Zapisujemy zmiany, używając .update(), aby nie wywołać sygnałów w pętli
    Trip.objects.filter(pk=trip.pk).update(
        total_distance_km=trip.total_distance_km,
        total_elevation_gain_m=trip.total_elevation_gain_m,
        got_points=trip.got_points,
        everest_diff_m=trip.everest_diff_m
    )
    logger.info(f"Przeliczono i zapisano statystyki dla wycieczki ID: {trip.id}")


def find_mesoregions_for_trip(trip):
    """
    Znajduje unikalną listę mezoregionów, przez które przebiega trasa,
    W KOLEJNOŚCI ich "odwiedzenia".
    """
    all_segments_coords = []
    for segment in trip.gpx_paths.order_by('sequence'):
        if segment.gpx_path:
            all_segments_coords.extend(segment.gpx_path.coords)

    if not all_segments_coords:
        return MesoRegion.objects.none()

    full_trip_linestring = LineString(all_segments_coords, srid=4326)

    potential_regions = MesoRegion.objects.filter(shape__intersects=full_trip_linestring)

    if not potential_regions.exists():
        return MesoRegion.objects.none()

    ordered_regions = []
    last_region_id = None

    step = max(1, len(all_segments_coords) // 100)

    for i in range(0, len(all_segments_coords), step):
        lon, lat, *_ = all_segments_coords[i]
        current_point = Point(lon, lat, srid=4326)

        for region in potential_regions:
            if region.shape.contains(current_point):
                if region.id != last_region_id:
                    if region not in ordered_regions:
                        ordered_regions.append(region)
                    last_region_id = region.id
                break

    return ordered_regions


# odznaki/services/trip_service.py
# ... (na końcu pliku) ...

from geopy.distance import geodesic
import json


def get_elevation_profile_data(trip: Trip) -> Optional[str]:
    """
    Wersja 2.0: Przygotowuje dane dla wykresu profilu wysokościowego,
    grupując je w osobne serie dla każdego segmentu, aby umożliwić
    kolorowanie zgodne z trasą.

    Returns:
        str: Dane w formacie JSON (lista słowników, gdzie każdy reprezentuje segment)
             lub None, jeśli trasa nie ma punktów.
    """
    segments_with_paths = trip.gpx_paths.order_by('sequence')

    if not segments_with_paths.exists() or not any(s.gpx_path for s in segments_with_paths):
        return None

    datasets = []
    cumulative_distance_m = 0.0
    last_point_coords = None

    for segment in segments_with_paths:
        if not segment.gpx_path or len(segment.gpx_path.coords) == 0:
            continue

        segment_data = []
        points = segment.gpx_path.coords

        # Aby zapewnić ciągłość, pierwszy punkt nowego segmentu musi być
        # identyczny z ostatnim punktem poprzedniego.
        if last_point_coords:
            # Używamy ostatniego punktu poprzedniego segmentu
            start_point_dist_km = cumulative_distance_m / 1000
            start_point_elev_m = last_point_coords[2] or 0
            segment_data.append([round(start_point_dist_km, 3), start_point_elev_m])

        for i in range(len(points)):
            current_point_coords = points[i]

            # Jeśli to nie jest pierwszy punkt segmentu (lub w ogóle trasy), oblicz dystans
            if last_point_coords:
                loc1 = (last_point_coords[1], last_point_coords[0])
                loc2 = (current_point_coords[1], current_point_coords[0])
                distance_segment_m = geodesic(loc1, loc2).meters
                cumulative_distance_m += distance_segment_m

            distance_km = cumulative_distance_m / 1000
            elevation_m = current_point_coords[2] or 0

            # Dla pierwszego punktu pierwszego segmentu, po prostu go dodaj
            if not last_point_coords:
                segment_data.append([0.0, elevation_m])
            else:
                segment_data.append([round(distance_km, 3), elevation_m])

            # Zaktualizuj ostatni znany punkt
            last_point_coords = current_point_coords

        datasets.append({
            'label': f"Segment {segment.sequence}",
            'color': segment.color,
            'data': segment_data,
        })

    # Zwracamy dane jako string JSON
    return json.dumps(datasets)