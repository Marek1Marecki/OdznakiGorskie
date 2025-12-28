"""Pomocnicze funkcje do formatowania danych.

Ten moduł zawiera funkcje pomocnicze do formatowania różnych typów danych,
takich jak liczby, daty, tekst itp., w celu zapewnienia spójności w całej aplikacji.
"""
from datetime import date, datetime
from typing import Optional, Any, List, Dict, Union
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def format_date_range(start_date: Optional[date], end_date: Optional[date] = None) -> str:
    """Formatuje zakres dat w czytelnej formie.
    
    Args:
        start_date: Data początkowa
        end_date: Data końcowa (opcjonalna)
        
    Returns:
        Sformatowany ciąg z zakresem dat, np. "1-3 stycznia 2023"
    """
    if not start_date and not end_date:
        return _("Brak daty")
        
    if not end_date or start_date == end_date:
        return format_date(start_date)
        
    if start_date.year != end_date.year:
        return f"{format_date(start_date)} - {format_date(end_date)}"
    elif start_date.month != end_date.month:
        return f"{start_date.day} {_(start_date.strftime('%B'))} - {end_date.day} {_(end_date.strftime('%B'))} {start_date.year}"
    else:
        return f"{start_date.day}-{end_date.day} {_(start_date.strftime('%B'))} {start_date.year}"


def format_date(value: Optional[date]) -> str:
    """Formatuje datę w czytelnej formie.
    
    Args:
        value: Data do sformatowania
        
    Returns:
        Sformatowany ciąg z datą, np. "1 stycznia 2023"
    """
    if not value:
        return _("Brak daty")
        
    return f"{value.day} {_(value.strftime('%B'))} {value.year}"


def format_datetime(value: Optional[datetime]) -> str:
    """Formatuje datę i godzinę w czytelnej formie.
    
    Args:
        value: Data i godzina do sformatowania
        
    Returns:
        Sformatowany ciąg z datą i godziną, np. "1 stycznia 2023, 14:30"
    """
    if not value:
        return _("Brak daty")
        
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
        
    return value.strftime(f"%d %B %Y, %H:%M")


def format_height(height: Optional[Union[int, float]]) -> str:
    """Formatuje wysokość z jednostką.
    
    Args:
        height: Wysokość w metrach nad poziomem morza lub None
        
    Returns:
        Sformatowany ciąg z wysokością i jednostką, np. "1234 m n.p.m."
        lub "Wysokość nieznana" jeśli wysokość jest None.
    """
    if height is not None:
        return f"{int(height)} m n.p.m."
    return _("Wysokość nieznana")


def format_full_name(name: str, secondary_name: str = '') -> str:
    """Formatuje pełną nazwę z drugą nazwą w nawiasie, jeśli istnieje.
    
    Args:
        name: Główna nazwa obiektu
        secondary_name: Dodatkowa nazwa obiektu (opcjonalna)
        
    Returns:
        Sformatowany ciąg zawierający główną nazwę i ewentualnie drugą nazwę w nawiasie.
    """
    if not secondary_name:
        return name
    return f"{name} ({secondary_name})"


def format_boolean(value: bool, true_text: str = 'Tak', false_text: str = 'Nie') -> str:
    """Formatuje wartość logiczną na tekst.
    
    Args:
        value: Wartość logiczna do sformatowania
        true_text: Tekst dla wartości True (domyślnie 'Tak')
        false_text: Tekst dla wartości False (domyślnie 'Nie')
        
    Returns:
        str: Tekst odpowiadający wartości logicznej
        
    Example:
        >>> format_boolean(True)
        'Tak'
        
        >>> format_boolean(False, 'Dostępny', 'Niedostępny')
        'Niedostępny'
        
    Note:
        Funkcja jest używana do konwersji wartości logicznych na przyjazne użytkownikowi
        komunikaty w interfejsie użytkownika. Domyślne wartości to 'Tak' i 'Nie',
        ale można je dostosować do kontekstu.
    """
    return true_text if value else false_text


def format_list(items: List[Any], empty_text: str = 'Brak') -> str:
    """Formatuje listę elementów jako tekst.
    
    Args:
        items: Lista elementów do sformatowania
        empty_text: Tekst wyświetlany, gdy lista jest pusta (domyślnie 'Brak')
        
    Returns:
        str: Sformatowany ciąg z elementami oddzielonymi przecinkami
        
    Example:
        >>> format_list(['jabłka', 'gruszki', 'śliwki'])
        'jabłka, gruszki, śliwki'
        
        >>> format_list([])
        'Brak'
        
        >>> format_list([1, 2, 3], empty_text='Brak danych')
        '1, 2, 3'
        
    Note:
        - Jeśli lista jest pusta, zwracany jest `empty_text`
        - Elementy są konwertowane na stringi za pomocą `str()`
        - Elementy są oddzielane przecinkami ze spacjami
    """
    if not items:
        return empty_text
    return ", ".join(str(item) for item in items)


def format_dict(dictionary: Dict[Any, Any], separator: str = ': ', item_separator: str = ', ') -> str:
    """Formatuje słownik jako tekst.
    
    Args:
        dictionary: Słownik do sformatowania
        separator: Separator między kluczem a wartością (domyślnie ': ')
        item_separator: Separator między elementami (domyślnie ', ')
        
    Returns:
        str: Sformatowany ciąg z elementami słownika w formie 'klucz: wartość'
        
    Example:
        >>> data = {'imię': 'Jan', 'nazwisko': 'Kowalski', 'wiek': 30}
        >>> format_dict(data)
        'imię: Jan, nazwisko: Kowalski, wiek: 30'
        
        >>> format_dict(data, separator=' -> ', item_separator=' | ')
        'imię -> Jan | nazwisko -> Kowalski | wiek -> 30'
        
    Note:
        - Klucze i wartości są konwertowane na stringi za pomocą `str()`
        - Pary klucz-wartość są łączone w formie 'klucz: wartość'
        - Domyślne formatowanie używa przecinków do oddzielania elementów
        - Pusty słownik zwraca pusty ciąg
    """
    if not dictionary:
        return '{}'
        
    return item_separator.join(f"{k}{separator}{v}" for k, v in dictionary.items())


def format_badge_degree(degree: str, badge_name: str = '') -> str:
    """Formatuje stopień odznaki w czytelnej formie.
    
    Args:
        degree: Stopień odznaki (np. 'gold', 'silver', 'bronze')
        badge_name: Nazwa odznaki (opcjonalna)
        
    Returns:
        str: Sformatowany ciąg z nazwą stopnia i ewentualnie nazwą odznaki
        
    Example:
        >>> format_badge_degree('gold')
        'Złota'
        
        >>> format_badge_degree('silver', 'Górska Odznaka Turystyczna')
        'Srebrna Górska Odznaka Turystyczna'
        
        >>> format_badge_degree('platinum')
        'Platynowa'
        
    Note:
        Obsługiwane stopnie odznak:
        - gold -> Złota
        - silver -> Srebrna
        - bronze -> Brązowa
        - platinum -> Platynowa
        - diamond -> Diamentowa
        - popular -> Popularna
        - small -> Mała
        - large -> Duża
        
        Jeśli stopień nie jest rozpoznany, zwracany jest oryginalny tekst z pierwszą wielką literą.
    """
    from django.utils.translation import gettext_lazy as _
    
    degree_names = {
        'gold': _('Złota'),
        'silver': _('Srebrna'),
        'bronze': _('Brązowa'),
    }
    
    degree_display = degree_names.get(degree.lower(), degree.capitalize())
    
    if badge_name:
        return f"{degree_display} {badge_name}"
    return degree_display


def format_booklet_type(booklet_type: str) -> str:
    """Formatuje typ książeczki w czytelnej formie.
    
    Args:
        booklet_type: Typ książeczki (np. 'electronic', 'paper')
        
    Returns:
        str: Sformatowana nazwa typu książeczki
        
    Example:
        >>> format_booklet_type('electronic')
        'Elektroniczna'
        
        >>> format_booklet_type('paper')
        'Papierowa'
        
    Note:
        Obsługiwane typy książeczek:
        - electronic -> Elektroniczna
        - paper -> Papierowa
        
        Jeśli typ nie jest rozpoznany, zwracany jest oryginalny tekst z pierwszą wielką literą.
        
    Raises:
        ValueError: Jeśli `booklet_type` jest pustym ciągiem
    """
    from django.utils.translation import gettext_lazy as _
    
    type_names = {
        'electronic': _('Elektroniczna'),
        'paper': _('Papierowa'),
    }
    
    return type_names.get(booklet_type.lower(), booklet_type.capitalize())
