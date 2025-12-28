"""
Moduł zawierający logikę biznesową związaną ze stopniami odznak (poziomami).
"""
import logging
from typing import List, Optional, Dict
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError

from odznaki.models import BadgeLevel, Visit
from odznaki.exceptions import ValidationError, DatesNotInSequenceError, BusinessLogicError, ValidationError

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from odznaki.models import BadgeLevel

logger = logging.getLogger(__name__)

# --- Logika Odczytu i Obliczeniowa ---

def get_badge_level_status(badge_level: 'BadgeLevel') -> str:
    """Zwraca tekstową reprezentację statusu stopnia odznaki."""
    if badge_level.collected_at:
        return "W kolekcji"
    if badge_level.received_at:
        return "Otrzymana"
    if badge_level.verified_at:
        return "Zweryfikowana"
    if badge_level.sent_at:
        return "Wysłana do weryfikacji"
    return "W trakcie zdobywania"

def format_badge_level(level_value: str) -> str:
    """Formatuje wartość poziomu do czytelnej formy."""
    return level_value.replace('_', ' ').title()

# --- Logika Zapisu (Write Logic) ---

def validate_badge_level(badge_level: BadgeLevel) -> None:
    """Wykonuje pełną walidację logiki biznesowej dla stopnia odznaki."""
    errors = {}

    if badge_level.badge:
        if badge_level.poi_count > badge_level.badge.total_poi_count:
            errors['poi_count'] = [
                f"Liczba obiektów ({badge_level.poi_count}) nie może być "
                f"większa niż w odznace ({badge_level.badge.total_poi_count})."
            ]

    dates = [
        ('sent_at', badge_level.sent_at),
        ('verified_at', badge_level.verified_at),
        ('received_at', badge_level.received_at),
        ('collected_at', badge_level.collected_at)
    ]

    is_any_date_set = any(date_val for _, date_val in dates)

    for i in range(len(dates) - 1):
        field1_name, date1 = dates[i]
        field2_name, date2 = dates[i+1]
        if date1 and date2 and date1 > date2:
            raise DatesNotInSequenceError(
                f"Data w '{field2_name}' nie może być wcześniejsza niż w '{field1_name}'.",
                error_dict={field2_name: f"Nie może być wcześniejsza niż {field1_name}."}
            )

    # --- NOWA, KLUCZOWA LOGIKA WALIDACJI ---
    if is_any_date_set:
        if not badge_level.badge:
            # To nie powinno się zdarzyć w normalnym użytkowaniu, ale jest to zabezpieczenie
            raise BusinessLogicError("Nie można ustawić dat dla stopnia, który nie jest przypisany do odznaki.")

        # 1. Pobierz wszystkie unikalne, zaliczone POI dla nadrzędnej odznaki
        poi_ids_in_badge = badge_level.badge.points_of_interest.values_list('id', flat=True)

        # Filtrujemy wizyty, aby pasowały do ram czasowych odznaki
        visits_qs = Visit.objects.filter(point_of_interest_id__in=poi_ids_in_badge)
        if badge_level.badge.start_date:
            visits_qs = visits_qs.filter(visit_date__gte=badge_level.badge.start_date)
        if badge_level.badge.end_date:
            visits_qs = visits_qs.filter(visit_date__lte=badge_level.badge.end_date)

        achieved_poi_count = visits_qs.values('point_of_interest_id').distinct().count()

        # 2. Porównaj liczbę zdobytych POI z liczbą wymaganą dla TEGO stopnia
        if achieved_poi_count < badge_level.poi_count:
            # Rzucamy nowym, bardziej precyzyjnym wyjątkiem
            raise BusinessLogicError(
                f"Nie można ustawić dat, ponieważ nie spełniono warunków dla tego stopnia. "
                f"Wymagane: {badge_level.poi_count} POI, zdobyto: {achieved_poi_count}."
            )
            # Można też rzucić ValidationError, aby pokazać błąd w formularzu admina,
            # ale BusinessLogicError jest tu bardziej semantyczny.
    # --- KONIEC NOWEJ LOGIKI ---

    if errors:
        raise ValidationError("Błąd walidacji danych stopnia odznaki.", error_dict=errors)

@transaction.atomic
def create_or_update_badge_level(badge_level: BadgeLevel, update_fields: Optional[List[str]] = None) -> BadgeLevel:
    """
    Centralna, bezpieczna funkcja do tworzenia i aktualizowania stopnia odznaki.
    
    Args:
        badge_level: Instancja modelu BadgeLevel do zapisania
        update_fields: Opcjonalna lista pól do aktualizacji
        
    Returns:
        Zapisany obiekt BadgeLevel
        
    Raises:
        ValidationError: W przypadku błędów walidacji
        DatesNotInSequenceError: Gdy daty nie są w poprawnej kolejności
        BadgeNotFullyAchievedError: Gdy próbujemy ustawić daty dla niezdobytej odznaki
    """
    from odznaki.models import BadgeLevel
    
    if not isinstance(badge_level, BadgeLevel):
        raise ValueError("Parametr badge_level musi być instancją modelu BadgeLevel")
    
    try:
        # Walidacja pól modelu (np. MinValueValidator dla poi_count)
        badge_level.full_clean()
        
        # Walidacja logiki biznesowej
        validate_badge_level(badge_level)
        
        # Zapis do bazy danych
        try:
            badge_level.save(update_fields=update_fields)
        except Exception as e:
            logger.error(f"Błąd podczas zapisu do bazy danych: {str(e)}")
            raise
        
        logger.info(f"Zapisano stopień odznaki: '{badge_level.level}' dla odznaki ID {badge_level.badge_id}")
        
        return badge_level
        
    except DjangoValidationError as e:
        raise ValidationError("Błąd walidacji pól.", error_dict=e.message_dict) from e
