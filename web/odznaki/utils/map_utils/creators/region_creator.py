# odznaki/utils/map_utils/creators/region_creator.py

import folium
from folium.plugins import HeatMap
from typing import List, Union

from django.db.models import QuerySet, Prefetch

from odznaki.models import PointOfInterest, Country, Voivodeship, MesoRegion, MacroRegion, SubProvince, Province, \
    BadgeRequirement
from odznaki.services.point_of_interest_service import calculate_poi_statuses
from odznaki.services.scoring_service import calculate_scores_for_queryset
from odznaki.services import geography_service
from ..builders import MapBuilder, PopupHelper, IconHelper
from ..config import STATUS_COLORS
from ...geo_helpers import find_neighboring_regions


class RegionMapCreator(MapBuilder):
    """
    Wersja 5.1: Implementacja progresywnego renderowania warstw.
    """

    def _add_layers(self, folium_map: folium.Map, **kwargs) -> List:
        """
        Główna metoda budująca warstwy, sterowana flagami z kwargs.
        """
        region_object = kwargs.get('region_object')
        if not region_object:
            return []

        # --- NOWA, GŁÓWNA LOGIKA DECYZYJNA ---

        # Zawsze rysuj HeatMapę, jeśli jest włączona
        if kwargs.get('show_heatmap', False):
            self._add_heatmap_layer(folium_map, **kwargs)

        # Rysuj indywidualne znaczniki tylko, jeśli flaga jest ustawiona
        if kwargs.get('show_pois', False):
            self._add_poi_markers(folium_map, **kwargs)

        # --- KONIEC NOWEJ LOGIKI ---

        # Sąsiedzi i kontur regionu są rysowane niezależnie
        if kwargs.get('show_neighbors', False):
            self._add_neighbors(folium_map, region_object)
        self._add_region_boundary(folium_map, region_object)

        return [region_object]

    def _add_poi_markers(self, folium_map: folium.Map, **kwargs):
        """
        Renderuje indywidualne znaczniki POI.
        Wersja 2.0: Inteligentnie decyduje o renderowaniu dymków (popup).
        """
        poi_list = kwargs.get('poi_list', [])
        poi_statuses = kwargs.get('poi_statuses', {})

        if not poi_list:
            return

        # --- NOWA, POPRAWNA LOGIKA DECYZYJNA ---
        # 1. Definiujemy próg, powyżej którego popupy są zbyt kosztowne.
        POPUP_THRESHOLD = 500

        # 2. Renderuj popupy tylko, jeśli liczba POI jest poniżej progu.
        render_popups = len(poi_list) <= POPUP_THRESHOLD
        # --- KONIEC NOWEJ LOGIKI ---

        marker_group = folium.FeatureGroup(name=f'Punkty POI ({len(poi_list)})', show=True)
        for poi in poi_list:
            status = poi_statuses.get(poi.id, 'default')

            # Jeśli mamy renderować popupy, używamy naszej standardowej, "bogatej" metody.
            if render_popups:
                self.create_poi_marker(poi, status).add_to(marker_group)

            # W przeciwnym razie, tworzymy "lekki" znacznik tylko z tooltipem.
            else:
                color = STATUS_COLORS.get(status, STATUS_COLORS['default'])
                icon_name, icon_angle = IconHelper.get_icon_info(poi.category)
                icon = IconHelper.create_folium_icon(color, icon_name, icon_angle)

                folium.Marker(
                    location=[poi.location.y, poi.location.x],
                    popup=None,  # Jawnie brak dymka
                    tooltip=poi.name,
                    icon=icon
                ).add_to(marker_group)

        folium_map.add_child(marker_group)


    def _add_heatmap_layer(self, folium_map: folium.Map, **kwargs):
        """Renderuje warstwę HeatMap na podstawie `poi_scores`."""
        poi_list = kwargs.get('poi_list', [])
        poi_scores = kwargs.get('poi_scores')

        if not poi_list or not poi_scores:
            return

        heatmap_data = []
        for poi in poi_list:
            score = poi_scores.get(poi.id, 0)
            if score > 0 and poi.location:
                heatmap_data.append([poi.location.y, poi.location.x, score])

        if heatmap_data:
            HeatMap(
                heatmap_data,
                name='Mapa Cieplna (Potencjał POI)',
                min_opacity=self.config.HEATMAP_MIN_OPACITY,
                radius=self.config.HEATMAP_RADIUS,
                blur=self.config.HEATMAP_BLUR,
                show=True  # HeatMapa jest teraz domyślną warstwą, więc ją pokazujemy
            ).add_to(folium_map)

    def _add_neighbors(self, folium_map: folium.Map, region_object):
        # Ta metoda pozostaje bez zmian
        neighbors = find_neighboring_regions(region_object)
        if not neighbors: return
        neighbor_group = folium.FeatureGroup(name='Sąsiedzi', show=False)  # Ukryta domyślnie
        folium_map.add_child(neighbor_group)
        for neighbor in neighbors:
            if neighbor.shape:
                popup = PopupHelper.create_neighbor_popup(neighbor, self.request)
                simplified = neighbor.shape.simplify(self.config.BOUNDARY_SIMPLIFY_TOLERANCE, preserve_topology=True)
                geom_to_use = simplified if not simplified.empty else neighbor.shape
                folium.GeoJson(
                    geom_to_use.json,
                    style_function=lambda x: {'fillColor': '#9ca3af', 'color': '#6b7280', 'weight': 1.5,
                                              'fillOpacity': 0.1},
                    highlight_function=lambda x: {'fillColor': '#6b7280', 'color': '#111827', 'weight': 3,
                                                  'fillOpacity': 0.25},
                    tooltip=neighbor.name,
                    popup=popup
                ).add_to(neighbor_group)

    def _add_region_boundary(self, folium_map: folium.Map, region_object):
        # Ta metoda pozostaje bez zmian
        if region_object.shape:
            folium.GeoJson(
                region_object.shape.json,
                name=f"Granice - {region_object.name}",
                style_function=lambda x: {'fillColor': '#3b82f6', 'color': '#2563eb', 'weight': 3, 'fillOpacity': 0.2},
                highlight_function=lambda x: {'fillColor': '#60a5fa', 'color': '#1d4ed8', 'weight': 4,
                                              'fillOpacity': 0.3}
            ).add_to(folium_map)