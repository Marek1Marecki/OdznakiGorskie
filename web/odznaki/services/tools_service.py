# odznaki/services/tools_service.py

import logging
from datetime import date, timedelta
from collections import defaultdict
from collections import Counter

from django.db.models import Q, Prefetch, Count, F
from django.contrib.gis.db.models.functions import Transform, Distance

from odznaki.models import Badge, BadgeRequirement ,PointOfInterest, Visit, Trip, TripSegment


logger = logging.getLogger(__name__)


def find_potential_visits_from_gpx(distance_m=250):
    """
    Analizuje wszystkie aktywne i nieukończone odznaki, znajduje brakujące
    punkty POI i przeszukuje historyczne trasy GPX w ich pobliżu.

    Args:
        distance_m (int): Maksymalna odległość w metrach od trasy, aby uznać
                          POI za "odkryty".

    Returns:
        list: Lista słowników, gdzie każdy słownik reprezentuje POI,
              dla którego znaleziono potencjalne zaliczenia.
    """
    logger.info("Rozpoczynam wyszukiwanie potencjalnych zaliczeń z tras GPX...")
    today = date.today()

    # --- Krok 1: Znajdź wszystkie "brakujące" POI z aktywnych odznak ---

    # Pobierz wszystkie aktywne i nieukończone odznaki
    active_badges = Badge.objects.filter(
        is_fully_achieved=False,
    ).filter(
        Q(start_date__lte=today) | Q(start_date__isnull=True)
    ).filter(
        Q(end_date__gte=today) | Q(end_date__isnull=True)
    ).prefetch_related('points_of_interest')

    # Zbierz ID wszystkich POI, które są wymagane w tych odznakach
    required_poi_ids = set()
    for badge in active_badges:
        for poi in badge.points_of_interest.all():
            required_poi_ids.add(poi.id)

    # Zbierz ID wszystkich POI, które mają już jakąkolwiek wizytę
    visited_poi_ids = set(Visit.objects.values_list('point_of_interest_id', flat=True))

    # Ostateczna lista ID punktów do sprawdzenia
    missing_poi_ids = required_poi_ids - visited_poi_ids

    if not missing_poi_ids:
        logger.info("Brak nieodwiedzonych POI w aktywnych odznakach. Kończę.")
        return []

    missing_pois = PointOfInterest.objects.filter(id__in=missing_poi_ids).exclude(location__isnull=True)
    logger.info(f"Znaleziono {missing_pois.count()} brakujących POI do analizy.")

    # --- Krok 2: Dla każdego brakującego POI, znajdź bliskie trasy GPX ---

    # Pobieramy wszystkie segmenty tras, które mają geometrię
    all_segments = TripSegment.objects.exclude(gpx_path__isnull=True).select_related('trip')

    results = defaultdict(lambda: {'poi': None, 'badges': [], 'potential_trips': []})

    for poi in missing_pois:
        # Transformujemy lokalizację POI do układu metrycznego
        poi_location_metric = poi.location.transform(3857, clone=True)

        # Znajdujemy segmenty, które przechodzą w pobliżu
        nearby_segments = all_segments.annotate(
            location_metric=Transform('gpx_path', 3857)
        ).filter(
            location_metric__dwithin=(poi_location_metric, distance_m)
        ).annotate(
            # Obliczamy dokładną odległość, aby ją wyświetlić
            distance=Distance('location_metric', poi_location_metric)
        ).order_by('distance')

        if nearby_segments.exists():
            # Wypełniamy dane dla znalezionego POI
            results[poi.id]['poi'] = poi

            # Dodajemy odznaki, do których należy ten POI
            for badge in active_badges:
                if poi.id in {p.id for p in badge.points_of_interest.all()}:
                    results[poi.id]['badges'].append(badge.name)

            # Dodajemy pasujące wycieczki
            # Używamy słownika, aby uniknąć duplikatów, jeśli kilka segmentów
            # tej samej wycieczki jest blisko
            trips_for_this_poi = {}
            for segment in nearby_segments:
                if segment.trip.id not in trips_for_this_poi:
                    # Wyciągamy wartość w metrach z obiektu Distance
                    distance_in_meters = segment.distance.m

                    trips_for_this_poi[segment.trip.id] = {
                        'trip': segment.trip,
                        'distance': round(distance_in_meters)  # Teraz zaokrąglamy zwykłą liczbę
                    }

            results[poi.id]['potential_trips'] = list(trips_for_this_poi.values())

    logger.info(f"Zakończono analizę. Znaleziono {len(results)} POI z potencjalnymi zaliczeniami.")

    # Konwertujemy słownik na listę i sortujemy
    final_list = sorted(list(results.values()), key=lambda x: x['poi'].name)

    return final_list


def find_badge_poi_count_discrepancies():
    """
    Znajduje odznaki, których zadeklarowana liczba POI (`total_poi_count`)
    nie zgadza się z rzeczywistą liczbą przypisanych wymagań (BadgeRequirement).

    Returns:
        QuerySet: QuerySet obiektów Badge, które mają niezgodność.
                  Każdy obiekt w QuerySet ma dodatkową adnotację `actual_poi_count`.
    """
    logger.info("Rozpoczynam audyt zgodności liczby POI w odznakach...")

    # Używamy `annotate`, aby zliczyć rzeczywistą liczbę powiązanych wymagań dla każdej odznaki.
    # To jest jedno, wydajne zapytanie do bazy danych.
    badges_with_actual_count = Badge.objects.annotate(
        actual_poi_count=Count('badge_requirements')
    )

    # Używamy `exclude` i `F()`, aby na poziomie bazy danych odfiltrować tylko te
    # odznaki, gdzie zadeklarowana liczba jest RÓŻNA od rzeczywistej.
    discrepancies = badges_with_actual_count.exclude(
        total_poi_count=F('actual_poi_count')
    ).order_by('name')

    logger.info(f"Znaleziono {discrepancies.count()} odznak z niezgodnością w liczbie POI.")

    return discrepancies


def find_orphaned_pois_with_context(id_proximity_range=5, time_proximity_minutes=60):
    """
    Znajduje wszystkie "osierocone" punkty POI (nieprzypisane do żadnej odznaki)
    i dostarcza dla nich kontekstowych sugestii na podstawie sąsiednich ID
    oraz czasu utworzenia.

    Args:
        id_proximity_range (int): Ile ID w przód i w tył sprawdzać.
        time_proximity_minutes (int): Ile minut w przód i w tył sprawdzać.

    Returns:
        list: Lista słowników, gdzie każdy reprezentuje "osieroconego" POI
              wraz z listami sugestii.
    """
    logger.info("Rozpoczynam audyt osieroconych POI...")

    # Krok 1: Znajdź wszystkie "osierocone" POI
    orphaned_pois = list(PointOfInterest.objects.filter(
        badge_requirement__isnull=True
    ).select_related('mesoregion').order_by('id'))

    if not orphaned_pois:
        logger.info("Nie znaleziono osieroconych POI. Kończę.")
        return []

    # Krok 2: Przygotuj mapę {poi_id: [lista odznak]} dla wszystkich NIE-osieroconych POI
    # To jest kluczowa optymalizacja, aby uniknąć zapytań w pętli.
    logger.info("Przygotowuję mapę powiązań POI-Odznaka dla wszystkich 'nie-osieroconych' POI...")
    badges_by_poi_id = defaultdict(list)
    # Pobieramy wszystkie wymagania, od razu z powiązanymi odznakami
    all_requirements = BadgeRequirement.objects.select_related('badge').all()
    for req in all_requirements:
        badges_by_poi_id[req.point_of_interest_id].append(req.badge)

    # Krok 3: Stwórz mapę {poi_id: obiekt POI} dla wszystkich "sąsiadów"
    neighbor_poi_ids = badges_by_poi_id.keys()
    poi_map = {poi.id: poi for poi in PointOfInterest.objects.filter(id__in=neighbor_poi_ids)}


    # Krok 4: Iteruj po "sierotach" i zbieraj sugestie, korzystając z przygotowanych map
    results = []
    logger.info(f"Analizuję {len(orphaned_pois)} osieroconych POI...")
    for orphan in orphaned_pois:
        # --- A. Analiza Bliskości ID ---
        id_suggestions = []
        start_id = orphan.id - id_proximity_range
        end_id = orphan.id + id_proximity_range + 1
        for neighbor_id in range(start_id, end_id):
            if neighbor_id == orphan.id:
                continue

            # Sprawdzamy nasze przygotowane wcześniej dane (bez zapytania do bazy!)
            if neighbor_id in badges_by_poi_id:
                neighbor_poi = poi_map.get(neighbor_id)
                neighbor_badges = badges_by_poi_id[neighbor_id]
                if neighbor_poi and neighbor_badges:
                    id_suggestions.append({
                        'neighbor_poi': neighbor_poi,
                        'badges': sorted(list(set(neighbor_badges)), key=lambda b: b.name) # Unikalne i posortowane
                    })

        # --- B. Analiza Czasowa ---
        temporal_suggestions = []
        time_window = timedelta(minutes=time_proximity_minutes)
        start_time = orphan.created_at - time_window
        end_time = orphan.created_at + time_window

        # To jest jedyne zapytanie w pętli, ale jest bardzo szybkie i ograniczone
        time_neighbors_qs = PointOfInterest.objects.filter(
            created_at__range=(start_time, end_time),
            id__in=neighbor_poi_ids  # Ograniczamy tylko do POI, które mają odznaki
        ).exclude(id=orphan.id).order_by('created_at')

        for neighbor_poi in time_neighbors_qs:
            neighbor_badges = badges_by_poi_id.get(neighbor_poi.id)
            if neighbor_badges:
                temporal_suggestions.append({
                    'neighbor_poi': neighbor_poi,
                    'badges': sorted(list(set(neighbor_badges)), key=lambda b: b.name)
                })

        all_suggested_badges = []
        for suggestion in id_suggestions:
            all_suggested_badges.extend(suggestion['badges'])
        for suggestion in temporal_suggestions:
            all_suggested_badges.extend(suggestion['badges'])

        # Używamy Counter do zliczenia wystąpień każdej odznaki
        from collections import Counter
        badge_counts = Counter(all_suggested_badges)

        # Sortujemy odznaki od najczęściej występującej
        # Wynik to lista krotek: [(<obiekt Badge>, <liczba_wystąpień>), ...]
        most_common_badges = badge_counts.most_common()

        # Dodaj do wyników tylko jeśli znaleziono jakiekolwiek sugestie
        if id_suggestions or temporal_suggestions:
            results.append({
                'orphan_poi': orphan,
                'id_suggestions': id_suggestions,
                'temporal_suggestions': temporal_suggestions,
                'most_common_badges': most_common_badges, # <-- Przekazujemy nowe dane
            })

    logger.info(f"Zakończono audyt. Znaleziono {len(results)} osieroconych POI z sugestiami.")
    return results
