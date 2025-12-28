"""Moduł zawierający pomocnicze funkcje do walidacji danych w modelach.

Zawiera funkcje do typowych operacji walidacyjnych, takich jak:
- Walidacja dat (np. czy data nie jest z przyszłości)
- Walidacja wymaganych pól
- Walidacja wartości liczbowych
- Walidacja zakresów
"""

from datetime import date
from typing import Dict, Any, Optional, Union, List, TypeVar, Generic
from django.core.exceptions import ValidationError
from django.utils import timezone

T = TypeVar('T', int, float)

def validate_date_not_in_future(
    date_value: Optional[date],
    errors: Dict[str, Any],
    field_name: str,
    field_label: Optional[str] = None
) -> None:
    """Sprawdza, czy data nie jest z przyszłości.
    
    Args:
        date_value: Wartość daty do walidacji
        errors: Słownik błędów, do którego zostanie dodany błąd, jeśli walidacja nie powiedzie się
        field_name: Nazwa pola do użycia w komunikacie błędu
        field_label: Etykieta pola używana w komunikacie błędu (opcjonalna, domyślnie taka sama jak field_name)
    """
    if date_value is None:
        return
        
    # Konwertuj datę na datetime o północy w bieżącej strefie czasowej
    current_tz = timezone.get_current_timezone()
    current_date = timezone.now().astimezone(current_tz).date()
    
    if date_value > current_date:
        field_label = field_label or field_name
        errors[field_name] = f'Data {field_label} nie może być z przyszłości.'

def validate_date_range(
    start_date_field: str,
    end_date_field: str,
    start_date: Optional[date],
    end_date: Optional[date],
    errors: Dict[str, Any],
    custom_message: Optional[str] = None
) -> None:
    """Sprawdza, czy zakres dat jest poprawny (start_date <= end_date).
    
    Args:
        start_date_field: Nazwa pola daty początkowej do użycia w komunikacie błędu
        end_date_field: Nazwa pola daty końcowej do użycia w komunikacie błędu
        start_date: Wartość daty początkowej
        end_date: Wartość daty końcowej
        errors: Słownik błędów, do którego zostanie dodany błąd, jeśli walidacja nie powiedzie się
        custom_message: Niestandardowy komunikat błędu (opcjonalny)
    """
    if start_date and end_date and start_date > end_date:
        errors[end_date_field] = (
            custom_message or 
            f'Data "{end_date_field}" nie może być wcześniejsza niż data "{start_date_field}".'
        )

def validate_required_fields(
    required_fields: Dict[str, Any],
    errors: Dict[str, Any],
    custom_messages: Optional[Dict[str, str]] = None
) -> None:
    """Sprawdza, czy wymagane pola nie są puste.
    
    Args:
        required_fields: Słownik, gdzie klucz to nazwa pola, a wartość to wartość do sprawdzenia
        errors: Słownik błędów, do którego zostaną dodane błędy, jeśli walidacja nie powiedzie się
        custom_messages: Słownik niestandardowych komunikatów błędów (klucz to nazwa pola, wartość to komunikat)
    """
    custom_messages = custom_messages or {}
    
    for field_name, field_value in required_fields.items():
        if field_value in (None, '', []) and field_name not in errors:
            errors[field_name] = custom_messages.get(
                field_name, 
                f'Pole {field_name} jest wymagane.'
            )

def validate_positive_number(
    field_name: str,
    value: Optional[Union[int, float]],
    errors: Dict[str, Any],
    allow_zero: bool = False,
    custom_message: Optional[str] = None
) -> None:
    """Sprawdza, czy wartość jest liczbą dodatnią (lub nieujemną, jeśli allow_zero=True).
    
    Args:
        field_name: Nazwa pola do użycia w komunikacie błędu
        value: Wartość do sprawdzenia
        errors: Słownik błędów, do którego zostanie dodany błąd, jeśli walidacja nie powiedzie się
        allow_zero: Czy zero jest dozwoloną wartością
        custom_message: Niestandardowy komunikat błędu (opcjonalny)
    """
    if value is not None:
        if (not allow_zero and value <= 0) or (allow_zero and value < 0):
            errors[field_name] = custom_message or (
                f'Wartość {field_name} musi być większa od ' 
                f'{"lub równa zero" if allow_zero else "zera"}.'
            )

def validate_min_max_values(
    field_name: str,
    value: T,
    min_value: Optional[T] = None,
    max_value: Optional[T] = None,
    errors: Optional[Dict[str, Any]] = None,
    custom_message: Optional[str] = None
) -> bool:
    """Sprawdza, czy wartość mieści się w określonym zakresie.
    
    Args:
        field_name: Nazwa pola do użycia w komunikacie błędu
        value: Wartość do sprawdzenia
        min_value: Minimalna dozwolona wartość (włącznie)
        max_value: Maksymalna dozwolona wartość (włącznie)
        errors: Opcjonalny słownik błędów, do którego zostanie dodany błąd, jeśli walidacja nie powiedzie się
        custom_message: Niestandardowy komunikat błędu (opcjonalny)
        
    Returns:
        bool: True jeśli walidacja powiodła się, w przeciwnym razie False
    """
    is_valid = True
    
    if min_value is not None and value < min_value:
        is_valid = False
        if errors is not None:
            errors[field_name] = custom_message or (
                f'Wartość {field_name} nie może być mniejsza niż {min_value}.'
            )
    
    if max_value is not None and value > max_value:
        is_valid = False
        if errors is not None:
            errors[field_name] = custom_message or (
                f'Wartość {field_name} nie może być większa niż {max_value}.'
            )
    
    return is_valid

def validate_choice(
    field_name: str,
    value: Any,
    valid_choices: list,
    errors: Dict[str, Any],
    custom_message: Optional[str] = None
) -> None:
    """Sprawdza, czy wartość należy do listy dozwolonych wartości.
    
    Args:
        field_name: Nazwa pola do użycia w komunikacie błędu
        value: Wartość do sprawdzenia
        valid_choices: Lista dozwolonych wartości
        errors: Słownik błędów, do którego zostanie dodany błąd, jeśli walidacja nie powiedzie się
        custom_message: Niestandardowy komunikat błędu (opcjonalny)
    """
    if value is not None and value not in valid_choices:
        errors[field_name] = custom_message or (
            f'Nieprawidłowa wartość dla pola {field_name}. ' 
            f'Dozwolone wartości to: {", ".join(map(str, valid_choices))}.'
        )

def validate_date_sequence(
    first_date_field: str,
    second_date_field: str,
    first_date: Optional[date],
    second_date: Optional[date],
    errors: Dict[str, Any],
    custom_message: Optional[str] = None
) -> None:
    """Sprawdza, czy druga data jest równa lub późniejsza niż pierwsza data.
    
    Args:
        first_date_field: Nazwa pierwszego pola daty do użycia w komunikacie błędu
        second_date_field: Nazwa drugiego pola daty do użycia w komunikacie błędu
        first_date: Pierwsza wartość daty (wcześniejsza)
        second_date: Druga wartość daty (późniejsza)
        errors: Słownik błędów, do którego zostanie dodany błąd, jeśli walidacja nie powiedzie się
        custom_message: Niestandardowy komunikat błędu (opcjonalny)
    """
    if first_date and second_date and second_date < first_date:
        errors[second_date_field] = custom_message or (
            f'Data {second_date_field} nie może być wcześniejsza niż data {first_date_field}.'
        )

def validate_badge_dates(
    start_date: Optional[date],
    end_date: Optional[date],
    errors: Dict[str, Any]
) -> None:
    """Waliduje zakres dat dla modelu Badge.
    
    Sprawdza, czy data zakończenia nie jest wcześniejsza niż data rozpoczęcia.
    
    Args:
        start_date: Data rozpoczęcia
        end_date: Data zakończenia
        errors: Słownik błędów, do którego zostaną dodane błędy
    """
    if start_date and end_date and end_date < start_date:
        errors['__all__'] = 'Data zakończenia nie może być wcześniejsza niż data rozpoczęcia.'

def validate_badge_degree_dates(
    sent_date: Optional[date],
    verified_date: Optional[date],
    received_date: Optional[date],
    is_fully_achieved: bool,
    errors: Dict[str, List[str]],
    prefix: str = ''
) -> None:
    """Waliduje daty w modelu BadgeDegree.
    
    Sprawdza:
    1. Czy daty są w poprawnej kolejności (sent <= verified <= received)
    2. Czy daty nie są z przyszłości
    3. Czy wszystkie wymagane daty są ustawione, gdy odznaka jest oznaczona jako w pełni zdobyta
    
    Args:
        sent_date: Data wysłania wniosku
        verified_date: Data weryfikacji
        received_date: Data otrzymania odznaki
        is_fully_achieved: Czy odznaka jest oznaczona jako w pełni zdobyta
        errors: Słownik błędów, do którego będą dodawane błędy
        prefix: Prefiks do dodania do kluczy w słowniku błędów (opcjonalny)
    """
    import logging
    from django.utils import timezone
    
    logger = logging.getLogger(__name__)
    
    logger.info("""
    ========================================
    ROZPOCZĘCIE WALIDACJI DAT BADGE DEGREE
    ========================================""")
    logger.info("Parametry wejściowe:")
    logger.info(f"- sent_date: {sent_date} (typ: {type(sent_date).__name__ if sent_date else 'None'})")
    logger.info(f"- verified_date: {verified_date} (typ: {type(verified_date).__name__ if verified_date else 'None'})")
    logger.info(f"- received_date: {received_date} (typ: {type(received_date).__name__ if received_date else 'None'})")
    logger.info(f"- is_fully_achieved: {is_fully_achieved}")
    logger.info(f"- prefix: '{prefix}'")
    logger.info(f"- errors (przed walidacją): {errors}")

    # Używamy timezone.now() zamiast date.today(), aby umożliwić mockowanie daty w testach
    today = timezone.now().date()
    logger.info(f"Dzisiejsza data (timezone.now().date()): {today}")
    
    # Sprawdzanie, czy odznaka jest oznaczona jako w pełni zdobyta, jeśli ustawiono jakąkolwiek datę
    if any([sent_date, verified_date, received_date]) and not is_fully_achieved:
        error_msg = 'Nie można ustawić dat, jeśli odznaka nie jest oznaczona jako w pełni zdobyta.'
        logger.warning(f"Błąd walidacji: {error_msg}")
        errors.setdefault('__all__', []).append(error_msg)
    
    # Sprawdzanie dat z przyszłości
    if sent_date:
        logger.info(f"Sprawdzanie daty wysłania: {sent_date} > {today} = {sent_date > today}")
        if sent_date > today:
            error_msg = 'Data wysłania nie może być z przyszłości'
            logger.warning(f"Błąd walidacji sent_date: {error_msg}")
            errors.setdefault('sent', []).append(error_msg)
    
    if verified_date:
        logger.info(f"Sprawdzanie daty weryfikacji: {verified_date} > {today} = {verified_date > today}")
        if verified_date > today:
            error_msg = 'Data weryfikacji nie może być z przyszłości'
            logger.warning(f"Błąd walidacji verified_date: {error_msg}")
            errors.setdefault('verified', []).append(error_msg)
    
    if received_date:
        logger.info(f"Sprawdzanie daty otrzymania: {received_date} > {today} = {received_date > today}")
        if received_date > today:
            error_msg = 'Data otrzymania nie może być z przyszłości'
            logger.warning(f"Błąd walidacji received_date: {error_msg}")
            errors.setdefault('received', []).append(error_msg)
    
    # Sprawdzanie kolejności dat
    if sent_date and verified_date:
        logger.info(f"Sprawdzanie kolejności: sent_date={sent_date} > verified_date={verified_date} = {sent_date > verified_date}")
        if sent_date > verified_date:
            error_msg = 'Data weryfikacji nie może być wcześniejsza niż data wysłania'
            logger.warning(f"Błąd walidacji kolejności: {error_msg}")
            errors.setdefault('verified', []).append(error_msg)
    
    if verified_date and received_date:
        logger.info(f"Sprawdzanie kolejności: verified_date={verified_date} > received_date={received_date} = {verified_date > received_date}")
        if verified_date > received_date:
            error_msg = 'Data otrzymania nie może być wcześniejsza niż data weryfikacji'
            logger.warning(f"Błąd walidacji kolejności: {error_msg}")
            errors.setdefault('received', []).append(error_msg)
    
    # Sprawdzanie, czy data weryfikacji jest ustawiona, jeśli ustawiono datę otrzymania
    if received_date and not verified_date:
        error_msg = 'Nie można ustawić daty otrzymania bez daty weryfikacji'
        logger.warning(f"Błąd walidacji: {error_msg}")
        errors.setdefault('verified', []).append(error_msg)
    
    # Sprawdzanie, czy data wysłania jest ustawiona, jeśli ustawiono datę weryfikacji
    if verified_date and not sent_date:
        error_msg = 'Nie można ustawić daty weryfikacji bez daty wysłania'
        logger.warning(f"Błąd walidacji: {error_msg}")
        errors.setdefault('sent', []).append(error_msg)
    
    logger.info(f"Zakończenie walidacji dat. Błędy: {errors}")

def validate_badge_degree_objects_count(
    objects_per_degree: int,
    badge_number_to_choose: int,
    errors: Dict[str, Any]
) -> None:
    """Waliduje liczbę obiektów w stopniu odznaki.
    
    Sprawdza, czy liczba obiektów w stopniu jest większa od zera i nie przekracza
    maksymalnej liczby obiektów do wyboru dla danej odznaki.
    
    Args:
        objects_per_degree: Liczba obiektów w stopniu
        badge_number_to_choose: Maksymalna liczba obiektów do wyboru dla odznaki
        errors: Słownik błędów, do którego zostaną dodane błędy
    """
    if objects_per_degree <= 0:
        errors['objects_per_degree'] = ['Liczba obiektów w stopniu musi być większa od zera.']
    elif objects_per_degree > badge_number_to_choose:
        errors['objects_per_degree'] = [
            f'Liczba obiektów w stopniu ({objects_per_degree}) nie może być większa '
            f'niż maksymalna liczba obiektów do wyboru dla tej odznaki ({badge_number_to_choose}).'
        ]
