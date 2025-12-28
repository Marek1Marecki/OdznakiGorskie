# odznaki/utils/map_utils/creators/heatmap_creator.py

import folium
from folium.plugins import HeatMap
from ..builders import MapBuilder


class HeatmapCreator(MapBuilder):
    """
    Kreator do generowania map cieplnych (np. ze śladów GPX).
    """

    def _add_layers(self, folium_map: folium.Map, **kwargs):
        heatmap_data = kwargs.get('heatmap_data')
        name = kwargs.get('name', 'Mapa Cieplna')
        radius = kwargs.get('radius', 12)
        blur = kwargs.get('blur', 8)

        if heatmap_data:
            HeatMap(
                heatmap_data,
                name=name,
                radius=radius,
                blur=blur,
                min_opacity=0.4
            ).add_to(folium_map)

        # Ta mapa nie ma konkretnych obiektów do wycentrowania,
        # więc zwracamy pustą listę.
        return []
