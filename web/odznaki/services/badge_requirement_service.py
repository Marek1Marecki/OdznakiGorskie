"""
Moduł zawierający logikę biznesową związaną z wymaganiami odznak (BadgeRequirement).
"""
import logging
from typing import List, Optional, Dict

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import QuerySet

from odznaki.models import BadgeRequirement, Badge, PointOfInterest, Visit
from odznaki.exceptions import ValidationError

logger = logging.getLogger(__name__)

# === Funkcje walidacyjne ===

def validate_badge_requirement(instance: BadgeRequirement) -> None:
    """Wykonuje pełną walidację logiki biznesowej dla wymagania odznaki."""
    try:
        # Używa wbudowanych walidatorów Django, w tym unique_together
        instance.full_clean()
    except DjangoValidationError as e:
        raise ValidationError("Błąd walidacji wymagania odznaki.", error_dict=e.message_dict) from e

# === Funkcje operacji na pojedynczym obiekcie ===

@transaction.atomic
def create_or_update_badge_requirement(
    badge: Badge,
    point_of_interest: PointOfInterest,
    obligatory: bool = False
) -> BadgeRequirement:
    """
    Tworzy lub aktualizuje wpis wymagania odznaki.
    Jest to preferowana metoda zapisu, zapewniająca walidację.
    """
    # Znajdź istniejący wpis lub utwórz nowy
    instance, created = BadgeRequirement.objects.get_or_create(
        badge=badge,
        point_of_interest=point_of_interest,
        defaults={'obligatory': obligatory}
    )

    if not created and instance.obligatory != obligatory:
        instance.obligatory = obligatory

    validate_badge_requirement(instance)
    instance.save()

    logger.info(f"{'Utworzono' if created else 'Zaktualizowano'} wymaganie odznaki: {instance}")
    return instance

def is_requirement_achieved(instance: BadgeRequirement) -> bool:
    """Sprawdza, czy powiązany punkt turystyczny został odwiedzony."""
    if not instance.point_of_interest_id:
        return False
    # Wykorzystujemy nową relację z modelu PointOfInterest
    return instance.point_of_interest.visits.exists()

# === Funkcje operujące na QuerySet ===

def get_requirements_for_badge(
    badge: Badge,
    only_obligatory: Optional[bool] = None
) -> QuerySet[BadgeRequirement]:
    """Zwraca QuerySet wymagań dla danej odznaki.
    
    Args:
        badge: Obiekt Badge, dla którego mają zostać pobrane wymagania
        only_obligatory: Jeśli True, zwraca tylko wymagania obowiązkowe
            Jeśli False, zwraca tylko opcjonalne. Jeśli None, zwraca wszystkie.
            
    Returns:
        QuerySet[BadgeRequirement]: Kwerenda z wymaganiami dla odznaki
    """
    qs = BadgeRequirement.objects.filter(badge=badge)
    if only_obligatory is not None:
        qs = qs.filter(obligatory=only_obligatory)
    return qs.select_related('point_of_interest')

def get_badges_for_poi(
    point_of_interest: PointOfInterest
) -> QuerySet[BadgeRequirement]:
    """Zwraca QuerySet wymagań, w których występuje dany punkt.
    
    Args:
        point_of_interest: Punkt, dla którego mają zostać znalezione odznaki
        
    Returns:
        QuerySet[BadgeRequirement]: Kwerenda z wymaganiami zawierającymi dany punkt
    """
    return BadgeRequirement.objects.filter(
        point_of_interest=point_of_interest
    ).select_related('badge')

# === Funkcje tworzenia obiektów ===
# Usunięto nieaktualną funkcję create_listofobjects, która operowała na starych modelach
# Zastąpiona przez nowocześniejszą funkcję create_or_update_badge_requirement
