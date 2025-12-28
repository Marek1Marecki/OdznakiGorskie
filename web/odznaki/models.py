# odznaki/models.py

# Ten plik służy jako punkt wejścia dla Django do importowania modeli
# z pakietu odznaki.models. Wszystkie modele są zdefiniowane w odpowiednich
# modułach wewnątrz katalogu models/.
# Zachowujemy ten plik dla kompatybilności wstecznej i zgodności z konwencjami Django.

from .models.badge import Badge
from .models.badge_level import BadgeLevel
from .models.badge_news_item import BadgeNewsItem
from .models.badge_requirement import BadgeRequirement
from .models.base import AbstractTimeStampedModel, LocationModel
from .models.booklet import Booklet, BookletType
from .models.geography import Country, Voivodeship, Province, SubProvince, MacroRegion, MesoRegion
from .models.organizer import Organizer
from .models.point_of_interest import PointOfInterest
from .models.point_of_interest_photo import PointOfInterestPhoto
from .models.trips import Trip, TripSegment
from .models.visit import Visit

# Opcjonalnie można dodać __all__ aby kontrolować co jest dostępne przy imporcie *
__all__ = [
    'AbstractTimeStampedModel', 'LocationModel',
    'Badge', 'BadgeLevel', 'BadgeNewsItem', 'BadgeRequirement',
    'Booklet', 'BookletType',
    'Country', 'Voivodeship', 'Province', 'SubProvince', 'MacroRegion', 'MesoRegion',
    'Organizer',
    'PointOfInterest', 'PointOfInterestPhoto',
    'Trip', 'TripSegment',
    'Visit',
]