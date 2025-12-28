"""Pomocnicze funkcje geograficzne i związane z hierarchią lokalizacji.

Ten moduł zawiera funkcje pomocnicze do wykonywania obliczeń
geograficznych, zarządzania hierarchią lokalizacji oraz operacji
na obiektach geograficznych.
"""
import math
from typing import Optional, List, TypeVar, Any
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.urls import reverse, NoReverseMatch

# Typ generyczny dla modeli hierarchicznych
HierarchicalModel = TypeVar('HierarchicalModel')


def get_hierarchy_path(hierarchy_objects, separator: str = ' > ') -> str:
    """Zwraca ścieżkę hierarchii jako ciąg znaków.
    
    Funkcja może przyjąć pojedynczy obiekt (wtedy sama zbuduje hierarchię)
    lub listę obiektów w hierarchii.
    
    Args:
        hierarchy_objects: Obiekt lub lista obiektów w hierarchii
        separator: Separator używany do łączenia nazw w ścieżce (domyślnie ' > ')
        
    Returns:
        str: Sformatowana ścieżka hierarchii, np. 'Polska > Małopolskie > Tatry'
        
    Example:
        >>> class Location:
        ...     def __init__(self, name, parent=None):
        ...         self.name = name
        ...         self.parent = parent
        ...     def get_parent(self):
        ...         return self.parent
        ...     def __str__(self):
        ...         return self.name
        >>> 
        >>> country = Location('Polska')
        >>> province = Location('Małopolskie', country)
        >>> mesoregion = Location('Tatry', province)
        >>> 
        >>> # Dla listy obiektów
        >>> get_hierarchy_path([country, province, mesoregion])
        'Polska > Małopolskie > Tatry'
        
        >>> # Dla pojedynczego obiektu (funkcja sama zbuduje hierarchię)
        >>> get_hierarchy_path(mesoregion)
        'Polska > Małopolskie > Tatry'
        
    Note:
        - Funkcja obsługuje obiekty z atrybutem 'name' lub metodą __str__
        - Automatycznie usuwa duplikaty w ścieżce
        - Jeśli obiekt nie ma atrybutu 'name', używana jest jego reprezentacja string
    """
    # Jeśli przekazano pojedynczy obiekt, zbuduj hierarchię
    if not isinstance(hierarchy_objects, (list, tuple)):
        hierarchy_objects = get_location_hierarchy(hierarchy_objects)
        
    # Wyciągnij nazwy obiektów, które mają atrybut 'name'
    names = []
    for obj in hierarchy_objects:
        if hasattr(obj, 'name'):
            name = str(obj.name)
            # Unikaj duplikatów w ścieżce (np. gdy obiekt jest w swojej własnej hierarchii)
            if not names or names[-1] != name:
                names.append(name)
                
    return separator.join(names)


def get_location_hierarchy(location, _recursion_guard=None) -> List[Any]:
    """Zwraca listę obiektów tworzących pełną hierarchię lokalizacji.
    
    Funkcja obsługuje obiekty z metodą get_parent() lub atrybutem parent.
    
    Args:
        location: Obiekt lokalizacji (może mieć metodę get_parent() lub atrybut parent)
        _recursion_guard: Wewnętrzny parametr do śledzenia odwiedzonych obiektów (używany do wykrywania cykli)
        
    Returns:
        Lista obiektów w hierarchii, posortowana od najwyższego do najniższego poziomu
        
    Przykład:
        # Dla obiektu z metodą get_parent()
        hierarchy = get_location_hierarchy(mesoregion)
        
        # Dla obiektu z atrybutem parent
        hierarchy = get_location_hierarchy(some_object)
    """
    if not location:
        return []
        
    # Inicjalizacja strażnika rekurencji przy pierwszym wywołaniu
    if _recursion_guard is None:
        _recursion_guard = set()
    
    # Sprawdź, czy nie ma cyklu w hierarchii
    location_id = id(location)
    if location_id in _recursion_guard:
        return [location]  # Znaleziono cykl, zwróć tylko bieżący obiekt
    
    # Dodaj bieżący obiekt do strażnika rekurencji
    _recursion_guard.add(location_id)
    
    # Sprawdź, czy obiekt ma metodę get_parent()
    if hasattr(location, 'get_parent') and callable(getattr(location, 'get_parent')):
        try:
            parent = location.get_parent()
        except Exception:
            parent = None
    # Lub atrybut parent
    elif hasattr(location, 'parent'):
        parent = getattr(location, 'parent')
        # Jeśli parent to callable (np. ForeignKey), wywołaj je
        if callable(parent):
            try:
                parent = parent()
            except Exception:
                parent = None
    else:
        parent = None
    
    # Jeśli znaleźliśmy rodzica, najpierw pobierz jego hierarchię
    if parent:
        hierarchy = get_location_hierarchy(parent, _recursion_guard)
    else:
        hierarchy = []
    
    # Dodaj bieżący obiekt na koniec hierarchii (jeśli go tam jeszcze nie ma)
    if location not in hierarchy:
        hierarchy.append(location)
    
    # Usuń bieżący obiekt ze strażnika przed powrotem
    _recursion_guard.discard(location_id)
    
    return hierarchy


def validate_location_geometry(shape, field_name='shape'):
    """Waliduje geometrię lokalizacji.
    
    Sprawdza podstawowe właściwości obiektu geometrii, takie jak:
    - czy nie jest pusty
    - czy ma ustawiony SRID (układ współrzędnych)
    
    Args:
        shape: Obiekt geometrii do walidacji (np. obiekt GEOSGeometry)
        field_name: Nazwa pola w słowniku błędów (domyślnie 'shape')
        
    Returns:
        dict: Słownik z błędami walidacji, gdzie kluczem jest nazwa pola,
              a wartością lista komunikatów błędów. Pusty słownik oznacza brak błędów.
              
    Example:
        >>> from django.contrib.gis.geos import Polygon, MultiPolygon, Point, LineString
        
        # Prawidłowa geometria - MultiPolygon
        >>> shape = MultiPolygon(Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0))), srid=4326)
        >>> validate_location_geometry(shape)
        {}
        
        # Prawidłowa geometria - LineString
        >>> line = LineString((0, 0), (1, 1), srid=4326)
        >>> validate_location_geometry(line)
        {}
        
        # Pusta geometria
        >>> from django.contrib.gis.geos import GeometryCollection
        >>> empty_shape = GeometryCollection()
        >>> validate_location_geometry(empty_shape)
        {'shape': ['Geometria nie może być pusta.']}
        
        # Brak SRID
        >>> no_srid = MultiPolygon(Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0))))
        >>> validate_location_geometry(no_srid)
        {'shape': ['Geometria musi mieć ustawiony SRID (układ współrzędnych).']}
    """
    errors = {}
    
    # Sprawdzamy, czy geometria jest pusta
    if shape is None or shape.empty:
        errors[field_name] = errors.get(field_name, []) + ['Geometria nie może być pusta.']
        return errors
    
    # Sprawdzamy, czy geometria ma ustawiony SRID
    if not hasattr(shape, 'srid') or not shape.srid:
        errors[field_name] = errors.get(field_name, []) + [
            'Geometria musi mieć ustawiony SRID (układ współrzędnych).'
        ]
    
    return errors


def get_breadcrumbs(location_object):
    """
    Tworzy listę "okruszków" (breadcrumbs) dla danego obiektu geograficznego,
    wzbogaconą o typ każdego regionu.
    """
    breadcrumbs = [{'name': 'Geografia', 'url': reverse('odznaki:geography-index')}]

    # get_hierarchy zwraca listę obiektów, np. [<Country...>, <Province...>]
    hierarchy = location_object.get_hierarchy()

    for item in hierarchy:
        model_name = item._meta.model_name
        # Pobieramy "ładną" nazwę typu z metadanych modelu
        type_display = item._meta.verbose_name.title()

        if model_name in ['country', 'province', 'subprovince', 'macroregion', 'mesoregion', 'voivodeship']:
            url = None
            try:
                url = reverse(
                    'odznaki:geography-region-detail',
                    kwargs={'model_name': model_name, 'pk': item.pk}
                )
            except NoReverseMatch:
                # Jeśli nie można wygenerować URL, używamy None
                pass
                
            # Dodajemy element do breadcrumbs, nawet jeśli nie udało się wygenerować URL
            if not breadcrumbs or (url and breadcrumbs[-1].get('url') != url):
                breadcrumbs.append({
                    'name': item.name,
                    'url': url,  # Może być None, jeśli nie udało się wygenerować URL
                    'type_display': type_display
                })

    return breadcrumbs


def get_all_child_mesoregions(region_object):
    """
    Dla danego obiektu geograficznego (np. Prowincji) zwraca QuerySet
    wszystkich Mezoregionów, które znajdują się pod nim w hierarchii.
    """
    from odznaki.models import Province, SubProvince, MacroRegion, MesoRegion, Country

    if isinstance(region_object, MesoRegion):
        return MesoRegion.objects.filter(pk=region_object.pk)
    if isinstance(region_object, MacroRegion):
        return MesoRegion.objects.filter(macroregion=region_object)
    if isinstance(region_object, SubProvince):
        return MesoRegion.objects.filter(macroregion__subprovince=region_object)
    if isinstance(region_object, Province):
        return MesoRegion.objects.filter(macroregion__subprovince__province=region_object)
    if isinstance(region_object, Country):
        return MesoRegion.objects.filter(macroregion__subprovince__province__country=region_object)

    return MesoRegion.objects.none()


def find_neighboring_regions(region_object, buffer_distance=0.0001, max_recursion=10):
    """
    Znajduje wszystkie regiony tego samego typu, które graniczą (dotykają)
    z danym regionem.

    Args:
        region_object: Instancja modelu geograficznego (np. MesoRegion).
        buffer_distance: Odległość bufora w stopniach używana do znalezienia sąsiadów.
                        Domyślnie 0.0001 stopnia (około 10 metrów).
        max_recursion: Maksymalna liczba rekurencyjnych wywołań funkcji z większym buforem.
                       Domyślnie 10, co daje maksymalny bufor około 0.1 stopnia (około 10 km).

    Returns:
        QuerySet: QuerySet zawierający sąsiadujące obiekty.
    """
    # Sprawdzamy, czy obiekt w ogóle ma geometrię
    if not region_object.shape:
        return region_object.__class__.objects.none()  # Zwróć pusty QuerySet

    # Wykonujemy zapytanie przestrzenne, aby znaleźć sąsiadów
    # Używamy .exclude(pk=...) aby nie znaleźć samego siebie
    qs = region_object.__class__.objects.exclude(pk=region_object.pk)

    # Tworzymy bufor wokół granicy regionu
    buffered_boundary = region_object.shape.buffer(buffer_distance)
    
    # Szukamy regionów, które przecinają się z buforowaną granicą
    neighbors = qs.filter(shape__intersects=buffered_boundary)
    
    # Jeśli nie znaleziono sąsiadów i nie przekroczono maksymalnego bufora, próbujemy z większym buforem
    max_buffer = 0.01  # Maksymalny bufor to 0.01 stopnia (około 1 km)
    if not neighbors.exists() and buffer_distance < max_buffer and max_recursion > 0:
        return find_neighboring_regions(
            region_object, 
            buffer_distance=min(buffer_distance * 2, max_buffer),
            max_recursion=max_recursion - 1
        )

    return neighbors

