"""
Moduł zawierający logikę biznesową związaną z organizatorami odznak.
"""
import logging
from typing import Dict, Optional, List
from datetime import date
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from odznaki.models import Organizer
from odznaki.exceptions import ValidationError, BusinessLogicError
from odznaki.utils.validation_helpers import validate_date_not_in_future

logger = logging.getLogger(__name__)

def _validate_organizer_dates(date_of_accession: Optional[date], 
                           statute_date: Optional[date]) -> Dict[str, list]:
    """Pomocnik walidujący daty. Zwraca słownik błędów."""
    errors = {}
    
    if statute_date and not date_of_accession:
        errors['date_of_accession'] = [_("Data przystąpienia jest wymagana, jeśli ustawiono datę regulaminu.")]
    
    if date_of_accession and statute_date and date_of_accession < statute_date:
        errors['date_of_accession'] = [_("Data przystąpienia nie może być wcześniejsza niż data regulaminu.")]
    
    return errors

def validate_organizer(organizer: Organizer) -> None:
    """
    Wykonuje pełną walidację organizatora.
    
    Args:
        organizer: Instancja modelu Organizer do walidacji
        
    Raises:
        ValidationError: Jeśli wystąpią błędy walidacji pól
        BusinessLogicError: Jeśli zostaną naruszone reguły biznesowe
    """
    errors = {}
    
    # Walidacja dat z przyszłości
    if organizer.date_of_accession:
        validate_date_not_in_future(organizer.date_of_accession, errors, 'date_of_accession')
    if organizer.statute_date:
        validate_date_not_in_future(organizer.statute_date, errors, 'statute_date')
    
    # Zbieranie błędów z funkcji pomocniczej
    errors.update(_validate_organizer_dates(organizer.date_of_accession, organizer.statute_date))
    
    # Reguła biznesowa: Jeśli odznaka klubowa jest wymagana, to jej skan musi być załączony.
    if organizer.decoration_required and not organizer.decoration_scan:
        errors['decoration_scan'] = [_('Skan odznaki klubowej jest wymagany, ponieważ zaznaczono pole "Wymagana odznaka klubowa".')]
    
    # Jeśli są błędy, rzucamy wyjątkiem
    if errors:
        raise ValidationError("Błąd walidacji organizatora.", error_dict=errors)

@transaction.atomic
def create_or_update_organizer(organizer: Organizer, update_fields: List[str] = None) -> Organizer:
    """
    Centralna funkcja do zapisu i walidacji organizatora.
    To jest teraz JEDYNY poprawny sposób na zapisanie obiektu Organizer.
    
    Args:
        organizer: Instancja modelu Organizer do zapisania
        update_fields: Lista pól do zaktualizowania (dla optymalizacji)
        
    Returns:
        Zapisana instancja Organizer.
        
    Raises:
        ValidationError: Jeśli wystąpią błędy walidacji pól lub logiki biznesowej.
        BusinessLogicError: W przypadku nieoczekiwanych błędów biznesowych.
        
    Example:
        >>> org = Organizer(name="PTTK")
        >>> saved_org = create_or_update_organizer(org)
        >>> saved_org.pk is not None
        True
    """
    try:
        # 1. Walidacja na poziomie pól (Django)
        try:
            organizer.full_clean()
        except DjangoValidationError as e:
            raise ValidationError("Błąd walidacji pól organizatora.", error_dict=e.message_dict)
            
        # 2. Walidacja logiki biznesowej
        validate_organizer(organizer)
        
        # 3. Zapis do bazy danych
        organizer.save(update_fields=update_fields)
        
        return organizer
        
    except (ValidationError, BusinessLogicError):
        # Ponownie rzucamy te same wyjątki, aby zachować ich oryginalny typ
        raise
    except Exception as e:
        # Logowanie nieoczekiwanych błędów
        logger.error(f"Nieoczekiwany błąd podczas zapisywania organizatora {organizer.name}: {str(e)}")
        # Opakowujemy nieznany błąd w nasz własny wyjątek
        raise BusinessLogicError(
            "Wystąpił nieoczekiwany błąd podczas zapisywania organizatora. Prosimy spróbować ponownie."
        ) from e

def get_organizer_stats(organizer: Organizer) -> Dict[str, int]:
    """
    Zwraca statystyki związane z organizatorem.
    
    Args:
        organizer: Instancja modelu Organizer
        
    Returns:
        dict: Słownik zawierający:
            - badges_count: Liczba odznak powiązanych z organizatorem
            - booklets_count: Liczba książeczek powiązanych z organizatorem
            - active_badges_count: Liczba aktywnych odznak
            - upcoming_events_count: Liczba nadchodzących wydarzeń
            
    Example:
        >>> org = Organizer.objects.get(pk=1)
        >>> stats = get_organizer_stats(org)
        >>> stats['badges_count']
        5
        >>> stats['booklets_count']
        12
        
    Note:
        Funkcja wykonuje zapytania do bazy danych, więc warto rozważyć 
        optymalizację przy częstym wywoływaniu.
    """
    stats = {
        'badges_count': organizer.badges.count(),
        'booklets_count': organizer.booklets.count(),
        'required_booklet': organizer.booklet_required,
        'required_decoration': organizer.decoration_required
    }
    
    return stats
