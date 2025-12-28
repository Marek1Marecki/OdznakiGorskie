# odznaki/services/asset_audit_service.py
import logging
from collections import defaultdict
from django.urls import reverse

from odznaki.models import (
    BadgeLevel, Booklet, Organizer, PointOfInterestPhoto, TripSegment
)

logger = logging.getLogger(__name__)

# "Mapa" modeli i pól, które będziemy skanować.
# To centralne miejsce konfiguracji audytu.
SCAN_MAP = {
    'badge_level': {
        'model': BadgeLevel,
        'field': 'image',
        'name_attr': '__str__', # Użyjemy metody __str__ do identyfikacji obiektu
    },
    'booklet_image': {
        'model': Booklet,
        'field': 'image',
        'name_attr': 'name',
    },
    'booklet_scan': {
        'model': Booklet,
        'field': 'scan',
        'name_attr': 'name',
    },
    'organizer': {
        'model': Organizer,
        'field': 'decoration_scan',
        'name_attr': 'name',
    },
    'poi_photo': {
        'model': PointOfInterestPhoto,
        'field': 'picture',
        'name_attr': '__str__',
    },
    'trip_segment': {
        'model': TripSegment,
        'field': 'gpx_file',
        'name_attr': '__str__',
    },
}

def run_asset_audit(models_to_scan: list):
    """
    Przeprowadza audyt integralności plików dla wybranych modeli.

    Args:
        models_to_scan (list): Lista kluczy z SCAN_MAP do przeskanowania.

    Returns:
        dict: Słownik z pogrupowanymi wynikami.
    """
    logger.info(f"Rozpoczynam audyt plików dla: {', '.join(models_to_scan)}")
    
    # defaultdict(list) automatycznie tworzy pustą listę, gdy odwołujemy się do nowego klucza
    audit_results = defaultdict(list)
    total_problems = 0

    for key in models_to_scan:
        if key not in SCAN_MAP:
            continue

        config = SCAN_MAP[key]
        model_class = config['model']
        field_name = config['field']
        name_attr = config['name_attr']
        
        # Budujemy dynamicznie zapytanie: znajdź obiekty, gdzie pole pliku nie jest puste
        # `__exact=''` filtruje puste stringi, `__isnull=False` filtruje NULL-e.
        filter_kwargs = {
            f"{field_name}__isnull": False,
        }
        # `exclude` z `Q` jest bezpieczniejsze dla pól, które mogą być ''
        from django.db.models import Q
        queryset = model_class.objects.exclude(Q(**{field_name: ''}) | Q(**{field_name: None}))
        
        category_name = model_class._meta.verbose_name_plural.title()
        
        logger.info(f"Skanowanie {queryset.count()} obiektów w kategorii '{category_name}'...")
        
        for instance in queryset:
            file_field = getattr(instance, field_name)
            
            # Sprawdzamy, czy plik istnieje na dysku
            if not file_field.storage.exists(file_field.name):
                total_problems += 1
                
                # Przygotowujemy dane o problemie
                problem_data = {
                    'object_name': getattr(instance, name_attr),
                    'field_name': field_name,
                    'missing_path': file_field.name,
                    'edit_url': reverse(f'admin:odznaki_{model_class._meta.model_name}_change', args=[instance.pk]),
                }
                audit_results[category_name].append(problem_data)

    logger.info(f"Audyt zakończony. Znaleziono łącznie {total_problems} problemów.")
    
    # Zwracamy posortowany słownik dla spójnej kolejności w szablonie
    return dict(sorted(audit_results.items()))
    