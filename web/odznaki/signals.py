# odznaki/signals.py

import logging
from django.db.models.signals import post_save,post_delete
from django.dispatch import receiver
from django.core.cache import cache

# ZMIANA: Importujemy tylko model, którego dotyczy sygnał
from .models.point_of_interest_photo import PointOfInterestPhoto
from .models import TripSegment
from .services import trip_service
from .models import Province, SubProvince, MacroRegion, MesoRegion
from .services import geography_service
from odznaki.models import Visit, Badge, BadgeRequirement


logger = logging.getLogger(__name__)


@receiver(post_delete, sender=PointOfInterestPhoto)
def on_picture_delete_cleanup_file(sender, instance, **kwargs):
    """
    Automatycznie usuwa plik zdjęcia z dysku PO usunięciu obiektu PointOfInterestPhoto.
    
    To jest bezpieczne podejście, ponieważ plik jest usuwany dopiero po
    pomyślnym usunięciu rekordu z bazy danych.
    """
    if instance.picture:
        try:
            # Używamy metody .delete(), która obsługuje różne systemy plików
            instance.picture.delete(save=False)
            logger.info(f"Sygnał post_delete: Pomyślnie usunięto plik fizyczny: {instance.picture.name}")
        except Exception as e:
            logger.error(f"Sygnał post_delete: Błąd podczas usuwania pliku {instance.picture.name}: {e}", exc_info=True)


@receiver([post_save, post_delete], sender=TripSegment)
def on_trip_segment_change(sender, instance, **kwargs):
    """
    Sygnał, który uruchamia się po każdej zmianie w segmentach wycieczki
    i przelicza statystyki dla nadrzędnej wycieczki.
    """
    if instance.trip:
        trip_service.recalculate_trip_stats(instance.trip)


def _handle_geography_change(sender, instance, **kwargs):
    """
    Wspólna funkcja logiczna wywoływana przez wszystkie sygnały geograficzne.
    """
    created = kwargs.get('created', False)
    if created:
        return

    logger.info(
        f"Sygnał `post_save` wykrył zmianę w {sender.__name__} (ID: {instance.id}). "
        f"Uruchamiam synchronizację POI w celu zapewnienia spójności."
    )
    geography_service.synchronize_poi_hierarchy(instance)

# Rejestrujemy OSOBNY "słuchacz" dla każdego modelu.
# Wszystkie wywołują tę samą funkcję pomocniczą.

@receiver(post_save, sender=Province)
def on_province_change(sender, instance, **kwargs):
    _handle_geography_change(sender, instance, **kwargs)

@receiver(post_save, sender=SubProvince)
def on_subprovince_change(sender, instance, **kwargs):
    _handle_geography_change(sender, instance, **kwargs)

@receiver(post_save, sender=MacroRegion)
def on_macroregion_change(sender, instance, **kwargs):
    _handle_geography_change(sender, instance, **kwargs)

@receiver(post_save, sender=MesoRegion)
def on_mesoregion_change(sender, instance, **kwargs):
    _handle_geography_change(sender, instance, **kwargs)


@receiver([post_save, post_delete], sender=Visit)
def invalidate_scoring_cache_on_visit_change(sender, instance, **kwargs):
    """
    Invaliduje WSZYSTKIE cache scoring gdy Visit zostanie dodany/zmieniony/usunięty.

    Flow:
    1. User dodaje Visit w admin
    2. Django wywołuje post_save
    3. Ten handler usuwa cache
    4. Następny request przelicza scoring z nowym Visit
    """
    # Usuń cache danych
    cache.delete('scoring_data_v1')

    # Usuń cache wyników
    cache.delete('dashboard_scores_full_v1')
    cache.delete('dashboard_scores_top_v1')

    # Usuń inne cache używane przez scoring
    cache.delete('full_poi_ranking_for_details')

    action = 'created' if kwargs.get('created') else 'updated/deleted'
    logger.info(
        f"All scoring caches invalidated: Visit {action} "
        f"(POI: {instance.point_of_interest_id})"
    )


@receiver([post_save, post_delete], sender=Badge)
def invalidate_scoring_cache_on_badge_change(sender, instance, **kwargs):
    """
    Invaliduje WSZYSTKIE cache scoring gdy Badge zostanie zmieniony.

    Przypadki użycia:
    - is_fully_achieved zmienione na True/False
    - start_date / end_date zmienione
    - Badge dodany/usunięty
    """
    cache.delete('scoring_data_v1')
    cache.delete('dashboard_scores_full_v1')
    cache.delete('dashboard_scores_top_v1')
    cache.delete('full_poi_ranking_for_details')

    logger.info(f"All scoring caches invalidated: Badge changed ({instance.name})")


@receiver([post_save, post_delete], sender=BadgeRequirement)
def invalidate_scoring_cache_on_requirement_change(sender, instance, **kwargs):
    """
    Invaliduje WSZYSTKIE cache scoring gdy BadgeRequirement się zmieni.

    Przypadki użycia:
    - Dodano nowy POI do Badge
    - Usunięto POI z Badge
    """
    cache.delete('scoring_data_v1')
    cache.delete('dashboard_scores_full_v1')
    cache.delete('dashboard_scores_top_v1')
    cache.delete('full_poi_ranking_for_details')

    logger.info(
        f"All scoring caches invalidated: BadgeRequirement changed "
        f"(Badge: {instance.badge_id}, POI: {instance.point_of_interest_id})"
    )