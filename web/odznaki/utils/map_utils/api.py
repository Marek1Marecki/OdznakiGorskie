# odznaki/utils/map_utils/api.py

from typing import List, Dict
from odznaki.models import PointOfInterest, Badge, Trip

# Importujemy nasze nowe, wyspecjalizowane kreatory
from .creators.badge_creator import BadgeMapCreator
from .creators.vicinity_creator import VicinityMapCreator
from .creators.region_creator import RegionMapCreator
from .creators.geo_audit_creator import GeoAuditMapCreator
from .creators.organizer_creator import OrganizerMapCreator
# ZMIANA JEST TUTAJ: importujemy obie klasy z trip_creator
from .creators.trip_creator import TripMapCreator, TripPreviewMapCreator
from .creators.segment_preview_creator import SegmentPreviewMapCreator
from .creators.proximity_group_creator import ProximityGroupMapCreator
from .creators.heatmap_creator import HeatmapCreator


def create_badge_map_with_folium(badge: Badge, visited_poi_ids: set, request) -> str:
    """Creates an interactive Folium map for the badge detail view."""
    creator = BadgeMapCreator(request=request)
    folium_map = creator.build(badge=badge, visited_poi_ids=visited_poi_ids)
    return folium_map._repr_html_()

def create_poi_vicinity_map(main_poi: PointOfInterest, request) -> str:
    """Creates a Folium map centered on a given POI, showing its surroundings."""
    creator = VicinityMapCreator(request=request, main_poi=main_poi)
    folium_map = creator.build(main_poi=main_poi)
    return folium_map._repr_html_()

def create_region_map_with_folium(request, **kwargs):
    """
    Tworzy mapę Folium dla regionu geograficznego,
    przyjmując wszystkie potrzebne dane jako argumenty kluczowe.
    """
    creator = RegionMapCreator(request=request)
    # Przekazujemy wszystkie otrzymane argumenty kluczowe bezpośrednio do metody build
    folium_map = creator.build(**kwargs)
    return folium_map

def create_geo_audit_map(poi: PointOfInterest, errors: List[Dict], request) -> str:
    """Creates a Folium map visualizing geometric inconsistency errors."""
    creator = GeoAuditMapCreator(request=request, poi=poi)
    folium_map = creator.build(poi=poi, errors=errors)
    return folium_map._repr_html_()


def create_organizer_map_with_folium(request, poi_queryset=None, badges_context_qs=None) -> str:
    """Creates an enhanced organizer map."""
    creator = OrganizerMapCreator(request=request)
    # Przekazujemy wszystkie otrzymane argumenty do metody build kreatora
    folium_map = creator.build(
        poi_queryset=poi_queryset,
        badges_context_qs=badges_context_qs
    )
    return folium_map._repr_html_()

def create_trip_map_with_folium(trip: Trip, nearby_pois_qs, request) -> str:
    """Creates a comprehensive trip map with enhanced features."""
    creator = TripMapCreator(request=request)
    folium_map = creator.build(trip=trip, nearby_pois_qs=nearby_pois_qs)
    return folium_map._repr_html_()

def create_segment_preview_map_with_folium(segment, request):
    """
    Tworzy i zwraca OBIEKT mapy Folium dla podglądu segmentu.
    """
    creator = SegmentPreviewMapCreator(request=request, segment=segment)
    folium_map = creator.build(segment=segment)
    return folium_map

def create_proximity_group_map(analyzed_pois_in_group, request):
    """Creates a Folium map showing all POIs in a proximity group."""
    creator = ProximityGroupMapCreator(request=request)
    folium_map = creator.build(analyzed_pois_in_group=analyzed_pois_in_group, request=request)
    return folium_map._repr_html_()

def create_trip_preview_map_for_admin(trip, request):
    """
    Tworzy uproszczoną mapę podglądową dla panelu admina,
    pokazującą tylko samą trasę wycieczki.
    """
    # Używamy dedykowanego, prostszego kreatora
    creator = TripPreviewMapCreator(request=request)
    folium_map = creator.build(trip=trip)
    return folium_map

def create_gpx_heatmap_with_folium(request, heatmap_data) -> str:
    """Tworzy mapę cieplną ze śladów GPX."""
    creator = HeatmapCreator(request=request)
    folium_map = creator.build(
        heatmap_data=heatmap_data,
        name='Gęstość Śladów GPX'
    )
    return folium_map._repr_html_()
