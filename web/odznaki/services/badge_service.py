"""
Moduł zawierający logikę biznesową związaną z odznakami turystycznymi.

Zawiera funkcje do:
- Zarządzania cyklem życia odznak (tworzenie, aktualizacja, usuwanie)
- Weryfikacji warunków zdobycia odznak
- Obliczania postępu w zdobywaniu odznak
- Zarządzania zależnościami między odznakami a punktami POI

Uwaga: Wszystkie operacje na odznakach powinny przechodzić przez funkcje tego modułu.
"""
import logging
from typing import List, Optional, Set, Dict, Any

from django.db import transaction
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q, QuerySet
from django.utils import timezone

from odznaki.models import Badge, BadgeRequirement, Visit, PointOfInterest
from odznaki.exceptions import ValidationError, BusinessLogicError

logger = logging.getLogger(__name__)

# --- Stałe konfiguracyjne (Twoja sugestia) ---
MAX_FUTURE_YEARS_VALIDATION = 10
MAX_PAST_YEARS_VALIDATION = 10
ACHIEVEMENT_CACHE_TIMEOUT = 3600  # 1 godzina w sekundach


# --- Logika Odczytu (Read Logic) ---

def get_badge_by_id(badge_id: int, only_active: bool = True) -> Optional[Badge]:
    """Znajduje odznakę po jej ID.
    
    Args:
        badge_id: ID odznaki do znalezienia (musi być dodatnią liczbą całkowitą)
        only_active: Czy zwracać tylko aktywne odznaki (domyślnie True)
        
    Returns:
        Badge: Znaleziona odznaka (lub tylko aktywna, jeśli only_active=True) 
               lub None, jeśli nie znaleziono lub (odznaka jest nieaktywna i only_active=True)
        
    Raises:
        ValueError: Jeśli przekazano nieprawidłowy format ID (nie dodatnia liczba całkowita)
    """
    # Walidacja wejścia
    if not isinstance(badge_id, int) or badge_id <= 0:
        raise ValueError("ID odznaki musi być dodatnią liczbą całkowitą")
    
    try:
        badge = Badge.objects.get(id=badge_id)
        if only_active:
            today = timezone.now().date()
            if (badge.start_date and badge.start_date > today) or \
               (badge.end_date and badge.end_date < today):
                return None
        return badge
    except (Badge.DoesNotExist, ValueError):
        return None


def get_active_badges() -> QuerySet[Badge]:
    """
    Zwraca QuerySet aktywnych odznak posortowanych według nazwy.
    Filtrowanie odbywa się w całości na poziomie bazy danych.
    
    Odznaka jest uznawana za aktywną, jeśli:
    - start_date jest ustawiony i jest w przeszłości lub dzisiaj LUB nie jest ustawiony
    - ORAZ end_date jest ustawiony i jest w przyszłości lub dzisiaj LUB nie jest ustawiony
    """
    today = timezone.now().date()
    return Badge.objects.filter(
        (Q(start_date__lte=today) | Q(start_date__isnull=True)) &
        (Q(end_date__gte=today) | Q(end_date__isnull=True))
    ).order_by('name')


def _get_badge_pois_queryset(badge: Optional[Badge], obligatory: Optional[bool] = None) -> QuerySet[PointOfInterest]:
    """Pobiera QuerySet punktów POI powiązanych z odznaką.
    
    Args:
        badge: Instancja modelu Badge lub None
        obligatory: Określa, czy mają być zwrócone punkty obowiązkowe (True),
                   opcjonalne (False) czy wszystkie (None)
                   
    Returns:
        QuerySet[PointOfInterest]: Kolekcja punktów POI spełniających kryteria
        
    Raises:
        ValueError: Jeśli badge jest None lub nie ma przypisanego ID
        
    Uwaga:
        Funkcja prywatna - używana przez inne metody tego modułu.
        Zawsze zwraca tylko aktywne punkty POI.
    """
    if badge is None:
        raise ValueError("Nie można przekazać None jako odznaki")
        
    if not hasattr(badge, 'id') or badge.id is None:
        return PointOfInterest.objects.none()
    query = Q(badge_requirement__badge=badge, is_active=True)
    if obligatory is not None:
        query &= Q(badge_requirement__obligatory=obligatory)
    return PointOfInterest.objects.filter(query).distinct()

def get_obligatory_pois(badge: Badge) -> QuerySet[PointOfInterest]:
    """Zwraca QuerySet obowiązkowych punktów POI dla odznaki."""
    return _get_badge_pois_queryset(badge, obligatory=True)

def get_optional_pois(badge: Badge) -> QuerySet[PointOfInterest]:
    """Zwraca QuerySet opcjonalnych punktów POI dla odznaki."""
    return _get_badge_pois_queryset(badge, obligatory=False)

def get_all_pois(badge: Badge) -> QuerySet[PointOfInterest]:
    """Zwraca QuerySet wszystkich punktów POI dla odznaki."""
    return _get_badge_pois_queryset(badge)

# --- Logika Obliczeniowa (Calculation Logic) ---

def clear_achievement_cache(badge: Optional[Badge]) -> None:
    """Czyści cache dla wyników sprawdzania warunków zdobycia odznaki.
    
    Args:
        badge: Instancja modelu Badge, dla której czyścimy cache, lub None
        
    Uwaga:
        Funkcja jest wywoływana automatycznie przy modyfikacjach,
        które mogą wpłynąć na status zdobycia odznaki.
        Jeśli przekazano None, funkcja nic nie robi i kończy działanie.
    """
    if badge is None or not hasattr(badge, 'pk') or not badge.pk:
        return
        
    cache.delete(f'badge_{badge.id}_fully_achieved')

def check_if_fully_achieved(badge: Badge, force_recalculate: bool = False) -> bool:
    """Sprawdza, czy spełnione są wszystkie warunki zdobycia odznaki."""
    if not badge.pk:
        return False

    cache_key = f'badge_{badge.id}_fully_achieved'
    if not force_recalculate:
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

    requirements = BadgeRequirement.objects.filter(
        badge=badge, 
        point_of_interest__is_active=True
    )
    if not requirements.exists():
        cache.set(cache_key, False, timeout=3600)
        return False

    obligatory_poi_ids = set(
        requirements.filter(obligatory=True)
        .values_list('point_of_interest_id', flat=True)
    )
    all_poi_ids = set(requirements.values_list('point_of_interest_id', flat=True))

    achieved_poi_ids = set(
        Visit.objects.filter(point_of_interest_id__in=all_poi_ids)
        .values_list('point_of_interest_id', flat=True)
    )

    if not obligatory_poi_ids.issubset(achieved_poi_ids):
        cache.set(cache_key, False, timeout=3600)
        return False

    if len(achieved_poi_ids) < badge.required_poi_count:
        cache.set(cache_key, False, timeout=3600)
        return False

    cache.set(cache_key, True, timeout=3600)
    return True

def calculate_completion_percentage(badge: Badge) -> float:
    """Oblicza procent ukończenia odznaki na podstawie liczby zdobytych punktów.
    
    Args:
        badge: Instancja modelu Badge do obliczeń
        
    Returns:
        float: Wartość procentowa ukończenia (0.0 - 100.0)
        
    Uwaga:
        - Wynik jest ograniczony do 100% nawet jeśli zdobyto więcej punktów niż wymagane.
        - Dla nowych odznak (bez required_poi_count) zwraca 0.0.
        - Zlicza tylko unikalne punkty POI (wiele wizyt w tym samym punkcie liczą się jako 1).
        - W przypadku odznak wielostopniowych, punkty z wyższych stopni są automatycznie
          liczone do stopni niższych.
    """
    if not badge.pk or getattr(badge, 'required_poi_count', 0) <= 0:
        return 0.0
    
    # Pobieramy wszystkie punkty POI przypisane do odznaki (aktywne i nieaktywne)
    all_pois = get_all_pois(badge)
    
    # Pobieramy wszystkie wizyty w punktach POI tej odznaki
    achieved_visits = Visit.objects.filter(
        point_of_interest__in=all_pois
    )
    
    # Pobieramy unikalne ID odwiedzonych punktów
    achieved_poi_ids = {v.point_of_interest_id for v in achieved_visits}
    
    # Liczymy liczbę unikalnych odwiedzonych punktów
    unique_achieved_count = len(achieved_poi_ids)
    
    # Obliczamy procent ukończenia
    if badge.required_poi_count <= 0:
        return 0.0
        
    # Obliczamy procent, ale nie przekraczamy 100%
    completion_percentage = (min(unique_achieved_count, badge.required_poi_count) / badge.required_poi_count) * 100.0
    
    # Zaokrąglamy do dwóch miejsc po przecinku
    return round(completion_percentage, 2)

def get_badge_progress(badge: Badge) -> Dict[str, Any]:
    """Generuje szczegółowy raport postępu w zdobywaniu odznaki.
    
    Args:
        badge: Instancja modelu Badge do analizy
        
    Returns:
        Dict[str, Any]: Słownik zawierający:
        - total_required (int): Wymagana liczba punktów do zdobycia
        - achieved_count (int): Liczba zdobytych punktów
        - progress_percentage (float): Procent ukończenia (0.0-100.0)
        - is_fully_achieved (bool): Czy odznaka jest w pełni zdobyta
        - obligatory_achieved (int): Liczba zdobytych punktów obowiązkowych
        - total_obligatory (int): Całkowita liczba punktów obowiązkowych
        
    Przykład:
        {
            'total_required': 10,
            'achieved_count': 5,
            'progress_percentage': 50.0,
            'is_fully_achieved': False,
            'obligatory_achieved': 3,
            'total_obligatory': 3
        }
    """
    if not badge.pk:
        return {
            'total_required': 0,
            'achieved_count': 0,
            'progress_percentage': 0,
            'is_fully_achieved': False,
            'obligatory_achieved': 0,
            'total_obligatory': 0
        }
    
    # Pobierz wszystkie wymagane punkty
    all_requirements = BadgeRequirement.objects.filter(badge=badge)
    poi_ids = list(all_requirements.values_list('point_of_interest_id', flat=True))
    
    # Pobierz osiągnięte punkty
    achieved_pois = set(
        Visit.objects.filter(
            point_of_interest_id__in=poi_ids
        ).values_list('point_of_interest_id', flat=True).distinct()
    )
    
    # Oblicz statystyki dla punktów obowiązkowych
    obligatory_requirements = all_requirements.filter(obligatory=True)
    obligatory_poi_ids = list(obligatory_requirements.values_list('point_of_interest_id', flat=True))
    obligatory_achieved = len(achieved_pois.intersection(obligatory_poi_ids))
    
    return {
        'total_required': badge.required_poi_count,
        'achieved_count': len(achieved_pois),
        'progress_percentage': calculate_completion_percentage(badge),
        'is_fully_achieved': check_if_fully_achieved(badge, force_recalculate=True),
        'obligatory_achieved': obligatory_achieved,
        'total_obligatory': len(obligatory_poi_ids)
    }


def update_completion_status(badge: Badge) -> None:
    """
    Aktualizuje status ukończenia odznaki.
    
    Uwaga: Ta funkcja jest używana głównie przez system do aktualizacji statusu
    po zmianach w powiązanych modelach. Do ręcznej aktualizacji lepiej użyć
    funkcji create_or_update_badge.
    
    Args:
        badge: Instancja modelu Badge do aktualizacji
    """
    if not badge.pk:
        return  # Nowa odznaka nie wymaga jeszcze aktualizacji
        
    is_achieved = check_if_fully_achieved(badge, force_recalculate=True)
    
    if badge.is_fully_achieved != is_achieved:
        # Używamy update, aby uniknąć wywołania metody save modelu
        Badge.objects.filter(pk=badge.pk).update(
            is_fully_achieved=is_achieved,
            updated_at=timezone.now()
        )
        logger.info(f"Zaktualizowano status odznaki {badge.id} na is_fully_achieved={is_achieved}")
    
    clear_achievement_cache(badge)


def validate_badge(badge: Badge, timezone_module=None) -> None:
    """Waliduje poprawność danych odznaki przed zapisem.
    
    Sprawdza:
    - Poprawność nazwy (niepusta, max 100 znaków)
    - Spójność dat (start_date <= end_date)
    - Poprawność liczby wymaganych punktów (dodatnia liczba całkowita)
    
    Args:
        badge: Instancja modelu Badge do walidacji
        timezone_module: Opcjonalny moduł timezone do użycia (domyślnie: django.utils.timezone)
        
    Raises:
        ValidationError: Jeśli dane są nieprawidłowe
        
    Uwagi:
        - Funkcja nie sprawdza unikalności nazwy w bazie danych
        - Sprawdza tylko podstawową poprawność formatu dat
    """
    # Używamy przekazanego modułu timezone lub domyślnego
    tz = timezone_module or timezone
    
    errors = {}
    
    # Walidacja nazwy
    if not badge.name or not badge.name.strip():
        errors['name'] = "Nazwa odznaki jest wymagana."
    elif len(badge.name) > 100:
        errors['name'] = "Nazwa odznaki nie może przekraczać 100 znaków."
    
    # Walidacja dat
    today = tz.now().date()
    if badge.start_date and badge.start_date > today + tz.timedelta(days=365*10):
        errors['start_date'] = "Data rozpoczęcia nie może być późniejsza niż 10 lat od dziś."
        
    if badge.end_date and badge.end_date < today - tz.timedelta(days=365*10):
        errors['end_date'] = "Data zakończenia nie może być wcześniejsza niż 10 lat temu."
        
    if badge.start_date and badge.end_date and badge.start_date > badge.end_date:
        errors['end_date'] = "Data zakończenia nie może być wcześniejsza niż data rozpoczęcia."
    
    # Walidacja liczby wymaganych punktów
    if not hasattr(badge, 'required_poi_count') or badge.required_poi_count is None:
        errors['required_poi_count'] = "Liczba wymaganych punktów jest wymagana."
    elif not isinstance(badge.required_poi_count, int) or badge.required_poi_count < 1:
        errors['required_poi_count'] = "Liczba wymaganych punktów musi być dodatnią liczbą całkowitą."
    
    if errors:
        # Tworzymy obiekt ValidationError z odpowiednim formatem błędów
        # Używamy pierwszego błędu jako głównego komunikatu
        first_error = next(iter(errors.values()))
        
        # Tworzymy słownik błędów w formacie oczekiwanym przez Django
        error_dict = {}
        for field, message in errors.items():
            error_dict[field] = [DjangoValidationError(message)]
        
        # Tworzymy główny błąd walidacji
        validation_error = DjangoValidationError(first_error, code='invalid')
        
        # Ustawiamy error_dict bezpośrednio
        validation_error.error_dict = error_dict
        
        raise validation_error


@transaction.atomic
def create_or_update_badge(
    badge: Optional[Badge] = None,
    update_fields: Optional[List[str]] = None,
    **kwargs
) -> Badge:
    """Główna funkcja do tworzenia i aktualizowania odznaki.
    
    Zapewnia spójność danych i unika problemów z nieskończonymi pętlami.
    Wykonuje następujące kroki:
    1. Utworzenie nowej odznaki, jeśli nie podano istniejącej
    2. Walidacja modelu Django
    3. Walidacja logiki biznesowej
    4. Zapis obiektu (z użyciem transakcji)
    5. Aktualizacja statusu ukończenia
    6. Aktualizacja powiązanych obiektów
    7. Zwrócenie zaktualizowanego obiektu
    
    Args:
        badge: Instancja modelu Badge do zapisania lub None, aby utworzyć nową
        update_fields: Opcjonalna lista pól do aktualizacji (domyślnie wszystkie)
        **kwargs: Dodatkowe argumenty przekazywane do metody save() lub do konstruktora nowej odznaki
        
    Returns:
        Badge: Zapisana i zaktualizowana instancja modelu Badge
        
    Raises:
        ValidationError: Jeśli wystąpi błąd walidacji danych
        BusinessLogicError: Jeśli wystąpi błąd logiki biznesowej
        
    Przykład użycia:
        # Tworzenie nowej odznaki
        badge = create_or_update_badge(name="Korona Gór Polski", required_poi_count=28)
        
        # Aktualizacja istniejącej odznaki
        badge = create_or_update_badge(existing_badge, name="Nowa nazwa")
    """
    # 1. Utwórz nową odznakę, jeśli nie podano istniejącej
    if badge is None:
        badge = Badge(**{k: v for k, v in kwargs.items() 
                        if k in [f.name for f in Badge._meta.get_fields()]})
        is_new = True
    else:
        # Aktualizuj istniejącą odznakę danymi z kwargs
        for key, value in kwargs.items():
            if hasattr(badge, key):
                setattr(badge, key, value)
        is_new = badge.pk is None
    
    # 2. Walidacja modelu Django
    try:
        badge.full_clean()
    except DjangoValidationError as e:
        raise ValidationError("Błąd walidacji pól modelu.", error_dict=e.message_dict)
    
    # 3. Walidacja logiki biznesowej
    validate_badge(badge)
    
    # 4. Zapisz obiekt w standardowy sposób
    if is_new:
        # Dla nowych obiektów używamy save() bez update_fields
        badge.save()
    else:
        # Dla istniejących obiektów używamy update_fields, jeśli podane
        save_kwargs = {}
        if update_fields is not None:
            save_kwargs['update_fields'] = update_fields
        badge.save(**save_kwargs)
    
    # 5. Aktualizacja statusu ukończenia
    is_achieved = check_if_fully_achieved(badge, force_recalculate=True)
    if badge.is_fully_achieved != is_achieved:
        # Używamy update, aby uniknąć ponownego wywołania sygnałów
        Badge.objects.filter(pk=badge.pk).update(
            is_fully_achieved=is_achieved,
            updated_at=timezone.now()
        )
        logger.info(f"Zaktualizowano status odznaki {badge.id} na is_fully_achieved={is_achieved}")
    
    # 6. Wyczyść cache
    clear_achievement_cache(badge)
    
    # 7. Pobierz zaktualizowany obiekt
    badge.refresh_from_db()
    
    return badge


@transaction.atomic
def update_related_badges(point_of_interest: PointOfInterest) -> None:
    """Aktualizuje status wszystkich odznak powiązanych z danym punktem POI.
    
    Funkcja powinna być wywoływana po każdej zmianie w punktach POI,
    które mogą wpłynąć na status zdobycia odznaki (np. dodanie/edycja wizyty).
    
    Args:
        point_of_interest: Instancja modelu PointOfInterest do aktualizacji
        
    Uwagi:
        - Funkcja działa w transakcji atomowej
        - Automatycznie czyści cache dla zaktualizowanych odznak
        - Uwzględnia tylko aktywne odznaki
    """
    from django.db import transaction
    
    if not point_of_interest.pk:
        return  # Nowy punkt, nie ma jeszcze powiązanych odznak
    
    # Znajdź wszystkie odznaki, które mają ten punkt jako wymagany
    badges_to_update = Badge.objects.filter(
        badge_requirements__point_of_interest=point_of_interest
    ).distinct()
    
    # Aktualizujemy status każdej odznaki
    with transaction.atomic():
        for badge in badges_to_update:
            try:
                update_completion_status(badge)
            except Exception as e:
                logger.error(
                    f"Błąd podczas aktualizacji statusu odznaki {badge.id}: {str(e)}",
                    exc_info=True
                )
                # Kontynuujemy aktualizację pozostałych odznak
                continue
    
    logger.info(f"Zaktualizowano {len(badges_to_update)} powiązanych odznak dla punktu POI ID: {point_of_interest.id}")
