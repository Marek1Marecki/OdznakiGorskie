"""
Moduł zawierający logikę biznesową związaną z wizytami w punktach turystycznych (Visit).
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from odznaki.models import Visit, PointOfInterest, Badge
from odznaki.exceptions import ValidationError
from odznaki.services import badge_service  # NOWOŚĆ: Import serwisu odznak

logger = logging.getLogger(__name__)

# === Funkcje walidacyjne ===

def validate_visit(visit: Visit) -> None:
    """
    Wykonuje pełną walidację logiki biznesowej dla wizyty.
    Wykorzystuje wbudowane w model walidatory (CheckConstraint, UniqueConstraint).
    """
    try:
        # Używamy full_clean() do uruchomienia wszystkich walidacji z modelu
        visit.full_clean()
    except DjangoValidationError as e:
        # Opakowujemy błąd Django w nasz własny, spójny typ wyjątku
        raise ValidationError("Błąd walidacji wizyty.", error_dict=e.message_dict) from e

# === Funkcje operacji na pojedynczym obiekcie ===

@transaction.atomic
def create_or_update_visit(visit: Visit, update_fields: Optional[List[str]] = None) -> Visit:
    """
    Centralna, bezpieczna funkcja do tworzenia i aktualizowania wizyty.
    Po zapisie automatycznie aktualizuje status wszystkich powiązanych odznak.
    """
    validate_visit(visit)
    visit.save(update_fields=update_fields)
    logger.info(f"Zapisano wizytę: {visit} (ID: {visit.id})")

    # Kluczowy element logiki biznesowej.
    # Po każdej zmianie w wizytach, musimy sprawdzić, czy nie wpłynęło to
    # na status zdobycia którejś z odznak powiązanych z tym punktem.
    badge_service.update_related_badges(visit.point_of_interest)
    
    return visit

@transaction.atomic
def delete_visit(visit: Visit) -> None:
    """
    Usuwa wizytę i aktualizuje status powiązanych odznak.
    """
    # Zapisujemy POI przed usunięciem, aby móc zaktualizować odznaki
    poi_to_update = visit.point_of_interest
    
    visit_id = visit.id
    visit.delete()
    logger.info(f"Usunięto wizytę (ID: {visit_id}) dla punktu: {poi_to_update.name}")
    
    # Usunięcie wizyty również wymaga aktualizacji odznak
    badge_service.update_related_badges(poi_to_update)

# === Funkcje operujące na QuerySet ===

def get_visits_for_poi(point_of_interest: PointOfInterest) -> QuerySet[Visit]:
    """Zwraca QuerySet wizyt dla konkretnego punktu turystycznego."""
    return Visit.objects.filter(point_of_interest=point_of_interest).order_by('-visit_date')

def get_visits_in_date_range(start_date: date, end_date: date) -> QuerySet[Visit]:
    """Zwraca QuerySet wizyt z określonego zakresu dat."""
    return Visit.objects.filter(visit_date__range=[start_date, end_date]).order_by('-visit_date')

def get_visits_this_year() -> QuerySet[Visit]:
    """Zwraca wizyty z bieżącego roku kalendarzowego."""
    current_year = timezone.now().year
    return Visit.objects.filter(visit_date__year=current_year).order_by('-visit_date')

def get_visits_with_related_data(queryset: QuerySet[Visit]) -> QuerySet[Visit]:
    """
    Optymalizuje zapytania poprzez pobranie powiązanych obiektów i ich
    danych geograficznych za pomocą jednego zapytania.
    """
    # Zaktualizowano ścieżkę do select_related
    return queryset.select_related(
        'point_of_interest__mesoregion__macroregion__subprovince__province__country'
    )
