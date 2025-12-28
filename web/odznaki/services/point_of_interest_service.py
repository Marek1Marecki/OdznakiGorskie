"""
Moduł zawierający logikę biznesową związaną z punktami turystycznymi (PointOfInterest).
"""
import logging
from functools import cached_property
from collections import defaultdict
from datetime import date, datetime
from typing import List, Optional, Dict, Any, Set

from django.contrib.gis.db.models.functions import Distance, Transform
from django.contrib.gis.geos import Point, LineString
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q, Prefetch
from django.urls import reverse
from django.utils.functional import cached_property
from django.template.loader import render_to_string as original_render_to_string

from odznaki.exceptions import ValidationError
from odznaki.models import (
    Badge, 
    BadgeRequirement, 
    Country, 
    MesoRegion, 
    PointOfInterest, 
    Visit, 
    Voivodeship
)

logger = logging.getLogger(__name__)


def validate_point_of_interest(poi: PointOfInterest) -> None:
    """
    Wykonuje pełną walidację logiki biznesowej i pól modelu dla punktu POI.
    Łączy walidację z modelu Django z dodatkowymi regułami biznesowymi.
    """
    # Krok 1: Przygotowanie danych (np. konwersja pustego stringa na None)
    if poi.code == "":
        poi.code = None

    # Krok 2: Uruchomienie walidacji z modelu Django
    try:
        poi.full_clean()
    except DjangoValidationError as e:
        # Jeśli walidacja Django się nie powiedzie, od razu rzucamy wyjątek
        raise ValidationError("Błąd walidacji pól.", error_dict=e.message_dict) from e

    # Krok 3: Dodatkowe, niestandardowe reguły biznesowe
    errors = {}
    if poi.parent and poi.parent.pk == poi.pk:
        error_msg = "Punkt nie może być własnym rodzicem"
        errors['parent'] = [error_msg]
        # Rzucamy wyjątek z komunikatem, który zawiera szczegóły błędu
        raise ValidationError(f"Błąd walidacji danych punktu POI: {error_msg}", error_dict=errors)

    if errors:
        raise ValidationError("Błąd walidacji danych punktu POI.", error_dict=errors)

@transaction.atomic
def create_or_update_point_of_interest(
    poi: PointOfInterest, 
    update_fields: Optional[List[str]] = None
) -> PointOfInterest:
    """
    Centralna, bezpieczna funkcja do tworzenia i aktualizowania punktu POI.
    To jest jedyny zalecany sposób zapisu obiektów PointOfInterest.
    """
    # Wywołujemy naszą skonsolidowaną funkcję walidacyjną
    validate_point_of_interest(poi)
    
    # Zapisujemy obiekt
    poi.save(update_fields=update_fields)
    
    # Logowanie informacji o zapisie
    logger.info(f"Zapisano punkt POI: '{poi.name}' (ID: {poi.id})")
    
    return poi


class POIStatusCalculator:
    """
    Wersja 3.1: Z w pełni poprawną i kontekstową logiką `_determine_status`.
    """

    def __init__(self, poi_queryset, badges_queryset=None):
        self.poi_list = list(poi_queryset)
        self.poi_ids = [poi.id for poi in self.poi_list]
        self.today = date.today()
        self.badges_queryset = badges_queryset

    def get_statuses(self) -> Dict[int, str]:
        """Główna metoda. Zwraca słownik {poi_id: status}."""
        result = {}
        for poi in self.poi_list:
            visit_dates = self.visit_dates_by_poi_id.get(poi.id, [])
            badges_data = self.requirements_data_by_poi_id.get(poi.id, [])
            result[poi.id] = self._determine_status(visit_dates, badges_data)
        return result

    @cached_property
    def visit_dates_by_poi_id(self) -> Dict[int, List[date]]:
        """Zwraca słownik {poi_id: [lista_dat_wizyt]}."""
        visits_qs = Visit.objects.filter(point_of_interest_id__in=self.poi_ids).values('point_of_interest_id',
                                                                                       'visit_date')
        data = defaultdict(list)
        for visit in visits_qs:
            data[visit['point_of_interest_id']].append(visit['visit_date'])
        return data

    @cached_property
    def requirements_data_by_poi_id(self) -> Dict[int, List[Dict]]:
        """
        Zwraca słownik {poi_id: [lista_danych_o_wymaganiach]}.
        """
        requirements_qs = BadgeRequirement.objects.filter(point_of_interest_id__in=self.poi_ids)
        if self.badges_queryset is not None:
            requirements_qs = requirements_qs.filter(badge__in=self.badges_queryset)
        requirements_qs = requirements_qs.values('point_of_interest_id', 'badge__is_fully_achieved',
                                                 'badge__start_date', 'badge__end_date')
        data = defaultdict(list)
        for req in requirements_qs:
            data[req['point_of_interest_id']].append({
                'is_fully_achieved': req['badge__is_fully_achieved'],
                'start_date': req['badge__start_date'],
                'end_date': req['badge__end_date'],
            })
        return data

    # --- NOWA, W PEŁNI POPRAWNA I KONTEKSTOWA WERSJA METODY ---
    def _determine_status(self, visit_dates: List[date], badges_data: List[Dict]) -> str:
        """
        Wersja 3.0: Poprawnie obsługuje kontekst i hierarchię statusów.
        """
        if not badges_data:
            return 'nieaktywny'

        active_badges_data = [
            badge_data for badge_data in badges_data
            if not badge_data['is_fully_achieved'] and
               (not badge_data['start_date'] or badge_data['start_date'] <= self.today) and
               (not badge_data['end_date'] or badge_data['end_date'] >= self.today)
        ]

        # Jeśli w BIEŻĄCYM KONTEKŚCIE (np. dla danego organizatora)
        # nie ma żadnych aktywnych odznak, to POI jest nieaktywny w tym kontekście.
        if not active_badges_data:
            return 'nieaktywny'

        # Zliczamy, ile aktywnych odznak w BIEŻĄCYM KONTEKŚCIE jest już zaliczonych
        claimed_badges_count = 0
        for badge_data in active_badges_data:
            is_claimed = any(
                (not badge_data['start_date'] or visit_date >= badge_data['start_date']) and
                (not badge_data['end_date'] or visit_date <= badge_data['end_date'])
                for visit_date in visit_dates
            )
            if is_claimed:
                claimed_badges_count += 1

        # Ostateczna, prosta logika decyzyjna:
        if claimed_badges_count == len(active_badges_data):
            # WSZYSTKIE aktywne odznaki w tym kontekście są zaliczone
            return 'zdobyty'
        elif bool(visit_dates):
            # Nie wszystkie są zaliczone, ALE istnieje jakakolwiek wizyta (nawet niepasująca)
            return 'do_ponowienia'
        else:
            # Nie wszystkie są zaliczone I nie ma żadnych wizyt w ogóle
            return 'niezdobyty'


# --- ZMIANA: Główna funkcja teraz akceptuje opcjonalny `badges_queryset` ---
def calculate_poi_statuses(poi_queryset, badges_queryset=None):
    """
    Oblicza statusy punktów POI.
    Opcjonalnie, może działać w kontekście podanego `badges_queryset`.
    """
    return POIStatusCalculator(poi_queryset, badges_queryset).get_statuses()


def find_proximal_poi_groups(distance_km=1.0):
    """
    Znajduje i analizuje grupy punktów POI, które znajdują się blisko siebie.
    Używa ulepszonej logiki do weryfikacji powiązań wewnątrz grupy.
    """
    logger.info(f"Rozpoczynam analizę bliskości POI w promieniu {distance_km} km...")
    distance_m = distance_km * 1000
    all_pois = list(PointOfInterest.objects.exclude(location__isnull=True).select_related('parent'))
    logger.info(f"Znaleziono {len(all_pois)} punktów do analizy")
    poi_map = {p.id: p for p in all_pois}

    processed_poi_ids = set()
    final_groups_as_ids = []

    for poi in all_pois:
        if poi.id in processed_poi_ids:
            continue

        # Jedno zapytanie o sąsiadów
        poi_location_metric = poi.location.transform(3857, clone=True)
        neighbors_ids = set(PointOfInterest.objects.annotate(
            location_metric=Transform('location', 3857)
        ).filter(
            location_metric__dwithin=(poi_location_metric, distance_m)
        ).values_list('id', flat=True))

        # --- GŁÓWNA POPRAWKA ---
        # Dodaj grupę tylko, jeśli ma więcej niż 1 element
        if len(neighbors_ids) > 1:
            final_groups_as_ids.append(list(neighbors_ids))

        # Oznacz wszystkich znalezionych sąsiadów jako przetworzonych
        processed_poi_ids.update(neighbors_ids)

    logger.info(f"Znaleziono {len(final_groups_as_ids)} grup bliskich sobie POI.")

    # --- Krok 2: ULEPSZONA ANALIZA KAŻDEJ ZNALEZIONEJ GRUPY ---
    analyzed_groups = []

    for group_ids in final_groups_as_ids:
        group_id_set = set(group_ids)
        pois_in_group = [poi_map[pid] for pid in group_ids]

        # --- NOWA LOGIKA ANALIZY ---
        roots = [p for p in pois_in_group if p.parent is None]
        children = [p for p in pois_in_group if p.parent is not None]

        is_group_ok = True
        # Warunek 1: Musi być dokładnie jeden "korzeń" (rodzic główny)
        if len(roots) != 1:
            is_group_ok = False
        else:
            # Warunek 2: Wszystkie "dzieci" muszą wskazywać na rodzica WEWNĄTRZ tej grupy
            for child in children:
                if child.parent.id not in group_id_set:
                    is_group_ok = False
                    break

        group_status = 'OK' if is_group_ok else 'Wymaga uwagi'
        # --- KONIEC NOWEJ LOGIKI ANALIZY ---

        # Obliczanie max odległości i przygotowanie danych (jak poprzednio, ale z nowym statusem)
        parent_candidate = roots[0] if roots else pois_in_group[0]
        max_distance = 0
        if parent_candidate.location:
            # Transformujemy lokalizację rodzica do układu metrycznego raz, dla wydajności
            parent_loc_metric = parent_candidate.location.transform(3857, clone=True)

            for poi in pois_in_group:
                if poi.id != parent_candidate.id and poi.location:
                    # Transformujemy lokalizację dziecka i obliczamy precyzyjną odległość w metrach
                    poi_loc_metric = poi.location.transform(3857, clone=True)
                    distance = parent_loc_metric.distance(poi_loc_metric)  # Wynik jest w metrach
                    if distance > max_distance:
                        max_distance = distance

        analyzed_pois = []
        for poi in pois_in_group:
            status = ''
            if poi.parent is None:
                status = 'Rodzic'
            elif poi.parent_id in group_id_set:
                status = 'Połączony'
            else:
                status = 'Błędne połączenie'  # Wskazuje na rodzica spoza grupy

            analyzed_pois.append({'poi': poi, 'link_status': status})

        analyzed_groups.append({
            'pois_in_group': analyzed_pois,
            'status': group_status,  # Dodajemy klucz 'status' dla kompatybilności z testami
            'group_status': group_status,  # Zachowujemy oryginalny klucz dla kompatybilności wstecznej
            'parent_candidate_name': parent_candidate.name,
            'poi_count': len(pois_in_group),
            'max_distance': max_distance,
        })

    logger.info("Zakończono analizę powiązań i odległości w grupach.")
    return analyzed_groups


def run_full_geo_audit(request):
    """
    Przeprowadza kompleksowy audyt spójności geograficznej dla wszystkich POI
    i zwraca listę znalezionych problemów.
    """
    # Import lokalny, aby uniknąć problemów z cyklicznymi zależnościami
    from odznaki.utils.map_utils import create_geo_audit_map

    logger.info("Rozpoczynam kompleksowy audyt geograficzny POI...")

    # Krok 1: Pobieramy wszystkie POI z pełną, zoptymalizowaną hierarchią.
    pois_to_check = PointOfInterest.objects.exclude(location__isnull=True).select_related(
        'mesoregion__macroregion__subprovince__province__country',
        'voivodeship'
        # Pole 'country' jest już pobierane przez ścieżkę fizycznogeograficzną
    )

    problematic_pois = []

    # Krok 2: Iterujemy po każdym POI i przeprowadzamy walidację.
    for poi in pois_to_check:
        errors = []
        hierarchy_to_check = []

        # a) Budujemy listę poziomów hierarchii fizycznogeograficznej
        if poi.mesoregion:
            # Sprawdzamy, czy cała ścieżka w górę istnieje, aby uniknąć błędów
            if (poi.mesoregion.macroregion and
                poi.mesoregion.macroregion.subprovince and
                poi.mesoregion.macroregion.subprovince.province and
                poi.mesoregion.macroregion.subprovince.province.country):
                hierarchy_to_check.extend([
                    (poi.mesoregion, 'Mezoregion'),
                    (poi.mesoregion.macroregion, 'Makroregion'),
                    (poi.mesoregion.macroregion.subprovince, 'Podprowincja'),
                    (poi.mesoregion.macroregion.subprovince.province, 'Prowincja'),
                    (poi.mesoregion.macroregion.subprovince.province.country, 'Kraj')
                ])

        # b) Dodajemy do sprawdzenia hierarchię administracyjną
        if poi.voivodeship:
            hierarchy_to_check.append((poi.voivodeship, 'Województwo'))

        # c) Walidujemy każdy poziom w hierarchii
        for region, level_name in hierarchy_to_check:
            # Tworzymy słownik błędu na początku pętli
            error_details = {
                'level': level_name,
                'expected_region': region,
                'status': '',
                'suggestion': None
            }

            if not region.shape:
                error_details['status'] = 'Pominięty (brak geometrii)'
                errors.append(error_details)
                continue

            if not region.shape.contains(poi.location):
                error_details['status'] = 'Niezgodny'
                try:
                    # Szukamy poprawnego regionu na tym samym poziomie
                    model_class = region.__class__
                    suggestions = list(model_class.objects.filter(shape__contains=poi.location))
                    error_details['suggestion'] = suggestions
                except Exception as e:
                    logger.warning(f"Nie udało się znaleźć sugestii dla POI {poi.id} na poziomie {level_name}: {e}")
                    error_details['suggestion'] = []

                errors.append(error_details)

        # d) Jeśli znaleziono jakiekolwiek problemy, dodajemy POI do listy wyników
        if errors:
            try:
                # Generujemy HTML mapy i od razu go wstawiamy
                error_map_html = create_geo_audit_map(poi, errors, request)
            except Exception as e:
                logger.error(f"Błąd podczas generowania mapy dla POI {poi.id}: {e}", exc_info=True)
                error_map_html = "<div class='alert alert-danger'>Błąd renderowania mapy.</div>"

            problematic_pois.append({
                'poi': poi,
                'errors': errors,
                'map_html': error_map_html
            })

    logger.info(f"Zakończono audyt. Znaleziono {len(problematic_pois)} problematycznych POI.")

    # Serwis ZAWSZE zwraca listę danych.
    return problematic_pois
