from .base import AbstractTimeStampedModel, LocationModel
from .geography import Country, Voivodeship, Province, SubProvince, MacroRegion, MesoRegion
from .booklet import Booklet, BookletType
from .badge import Badge
from .badge_level import BadgeLevel
from .organizer import Organizer
from .point_of_interest import PointOfInterest
from .visit import Visit
from .badge_requirement import BadgeRequirement
from .point_of_interest_photo import PointOfInterestPhoto
from .trips import Trip, TripSegment
from .badge_news_item import BadgeNewsItem

# Możesz też zdefiniować __all__, aby kontrolować, co jest importowane
# przy 'from odznaki.models import *', ale powyższe importy są kluczowe.
__all__ = [
    'AbstractTimeStampedModel', 'LocationModel',
    'Country', 'Voivodeship', 'Province', 'SubProvince', 'MacroRegion', 'MesoRegion',
    'PointOfInterest',
    'Visit',
    'Booklet', 'BookletType',
    'Badge', 'BadgeLevel', 'BadgeRequirement',
    'Organizer',
    'Trip', 'TripSegment',
    'PointOfInterestPhoto',
    'BadgeNewsItem',
]
