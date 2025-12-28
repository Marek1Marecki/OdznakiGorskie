# odznaki/utils/map_utils/creators/geo_audit_creator.py

import folium
from typing import List, Dict

from odznaki.models import PointOfInterest
from ..builders import MapBuilder, IconHelper, PopupHelper
from ..config import MapConfig


class GeoAuditMapCreator(MapBuilder):
    """Creator for geo audit maps visualizing geometric inconsistency errors."""

    def __init__(self, request, poi: PointOfInterest):
        super().__init__(
            request,
            location=[poi.location.y, poi.location.x] if poi.location else None,
            zoom=MapConfig.AUDIT_ZOOM
        )

    def _add_layers(self, folium_map: folium.Map, **kwargs):
        poi = kwargs.get('poi')
        errors = kwargs.get('errors', [])
        if not poi or not poi.location: return []

        self._add_error_poi_marker(folium_map, poi)
        self._add_expected_region_boundaries(folium_map, errors)
        return [poi]

    def _add_error_poi_marker(self, folium_map: folium.Map, poi: PointOfInterest):
        icon = IconHelper.create_folium_icon('red', 'map-marker-alt')
        popup = PopupHelper.create_poi_popup(poi, self.request)
        folium.Marker(
            location=[poi.location.y, poi.location.x],
            popup=popup, tooltip=f"BŁĄD: {poi.name}", icon=icon
        ).add_to(folium_map)

    def _add_expected_region_boundaries(self, folium_map: folium.Map, errors: List[Dict]):
        """
        Dodaje do mapy warstwy z konturami "oczekiwanych" regionów,
        aby zwizualizować błąd niezgodności.
        """
        boundaries_group = folium.FeatureGroup(name='Oczekiwane granice', show=True)
        folium_map.add_child(boundaries_group)

        for error in errors:
            if error.get('status') == 'Niezgodny':
                expected_region = error.get('expected_region')

                if expected_region and expected_region.shape:
                    # Używamy `self.request` z klasy bazowej do stworzenia dymka
                    popup = PopupHelper.create_neighbor_popup(expected_region, self.request)

                    folium.GeoJson(
                        expected_region.shape.json,
                        name=f"Oczekiwano: {expected_region.name}",
                        style_function=lambda x: {
                            'fillColor': 'blue',
                            'color': 'blue',
                            'weight': 2,
                            'fillOpacity': 0.1
                        },
                        tooltip=f"Oczekiwany region: {expected_region.name}",
                        popup=popup
                    ).add_to(boundaries_group)
