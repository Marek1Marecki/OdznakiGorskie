# odznaki/services/geography_service.py

from typing import TYPE_CHECKING
import logging
from django.db import transaction

# Importujemy wszystkie potrzebne modele geograficzne oraz PointOfInterest
from odznaki.models import (
    Country, Province, SubProvince, MacroRegion, MesoRegion, Voivodeship,
    PointOfInterest
)

if TYPE_CHECKING:
    from odznaki.models import MesoRegion

logger = logging.getLogger(__name__)


def get_mesoregion_display_name(mesoregion: 'MesoRegion') -> str:
    """
    Generuje nazwę wyświetlaną dla obiektu mezoregionu.
    """
    # Ta funkcja pozostaje bez zmian
    MesoRegionModel = mesoregion.__class__
    is_ambiguous = MesoRegionModel.objects.filter(name=mesoregion.name).exclude(pk=mesoregion.pk).exists()
    if is_ambiguous:
        hierarchy = mesoregion.get_hierarchy()
        # Poprawka: get_hierarchy zwraca listę, bierzemy pierwszy element (kraj)
        country = hierarchy[0] if hierarchy else None
        if country and hasattr(country, 'code') and country.code:
            return f"{mesoregion.name} ({country.code})"
    return mesoregion.name


def get_pois_for_region(region_object):
    """
    Zwraca QuerySet wszystkich punktów POI znajdujących się w danym regionie,
    używając ZDENORMALIZOWANYCH pól dla błyskawicznej odpowiedzi.
    """
    # Importy wewnątrz funkcji dla pewności
    from odznaki.models import PointOfInterest, Country, Voivodeship, Province, SubProvince, MacroRegion, MesoRegion

    # Używamy `elif` dla lepszej czytelności i wydajności
    if isinstance(region_object, Country):
        # STARE (wolne): return PointOfInterest.objects.filter(mesoregion__macroregion__subprovince__province__country=region_object)
        # NOWE (błyskawiczne):
        return PointOfInterest.objects.filter(country=region_object)

    elif isinstance(region_object, Province):
        # STARE (wolne): return PointOfInterest.objects.filter(mesoregion__macroregion__subprovince__province=region_object)
        # NOWE (błyskawiczne):
        return PointOfInterest.objects.filter(province=region_object)

    elif isinstance(region_object, SubProvince):
        # STARE (wolne): return PointOfInterest.objects.filter(mesoregion__macroregion__subprovince=region_object)
        # NOWE (błyskawiczne):
        return PointOfInterest.objects.filter(subprovince=region_object)

    elif isinstance(region_object, MacroRegion):
        # STARE (wolne): return PointOfInterest.objects.filter(mesoregion__macroregion=region_object)
        # NOWE (błyskawiczne):
        return PointOfInterest.objects.filter(macroregion=region_object)

    elif isinstance(region_object, MesoRegion):
        # Tu nic się nie zmienia, bo to była już bezpośrednia relacja
        return PointOfInterest.objects.filter(mesoregion=region_object)

    elif isinstance(region_object, Voivodeship):
        # Tu nic się nie zmienia
        return PointOfInterest.objects.filter(voivodeship=region_object)

    # Fallback: jeśli typ obiektu jest nieznany, zwróć pusty QuerySet
    return PointOfInterest.objects.none()


@transaction.atomic
def synchronize_poi_hierarchy(region_instance):
    """
    Synchronizuje zdenormalizowane pola w PointOfInterest po zmianie
    w nadrzędnym regionie geograficznym.
    """
    logger.info(f"Rozpoczynam synchronizację hierarchii dla regionu: {region_instance.name}")

    # Znajdź wszystkie POI, których dotyczy zmiana.
    # Musimy użyć tutaj starych, "wolnych" złączeń, ponieważ
    # zakładamy, że zdenormalizowane pola mogą być nieaktualne.

    # Wybieramy odpowiedni filtr w zależności od typu zmienionego regionu
    if isinstance(region_instance, MesoRegion):
        pois_to_update = PointOfInterest.objects.filter(mesoregion=region_instance)
    elif isinstance(region_instance, MacroRegion):
        pois_to_update = PointOfInterest.objects.filter(mesoregion__macroregion=region_instance)
    elif isinstance(region_instance, SubProvince):
        pois_to_update = PointOfInterest.objects.filter(mesoregion__macroregion__subprovince=region_instance)
    elif isinstance(region_instance, Province):
        pois_to_update = PointOfInterest.objects.filter(mesoregion__macroregion__subprovince__province=region_instance)
    else:
        # Nieznany typ regionu, nie rób nic
        logger.warning(f"Otrzymano nieznany typ regionu do synchronizacji: {type(region_instance)}")
        return

    poi_count = pois_to_update.count()
    if poi_count == 0:
        logger.info("Brak punktów POI do zsynchronizowania dla tego regionu.")
        return

    logger.info(f"Znaleziono {poi_count} punktów POI do zsynchronizowania. Rozpoczynam pętlę...")

    # Używamy .iterator() dla wydajności przy dużej liczbie POI
    updated_count = 0
    for poi in pois_to_update.select_related('mesoregion__macroregion__subprovince__province').iterator():
        # Metoda .save() w modelu POI zawiera już logikę, która
        # poprawnie wypełnia zdenormalizowane pola. Po prostu ją wywołujemy.
        poi.save()
        updated_count += 1

    logger.info(f"Zakończono synchronizację. Zaktualizowano {updated_count} punktów POI.")
