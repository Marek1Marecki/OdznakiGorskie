import folium
from typing import List, Dict, Optional
from odznaki.models import PointOfInterest
from ..builders import MapBuilder, IconHelper, PopupHelper

class ProximityGroupMapCreator(MapBuilder):
    """Creator for proximity group analysis maps"""

    def _add_layers(self, folium_map: folium.Map, **kwargs):
        """Dodaje połączenia, markery i legendę. Zwraca listę POI do fit_bounds."""
        analyzed_pois_in_group = kwargs.get('analyzed_pois_in_group', [])
        pois = [item['poi'] for item in analyzed_pois_in_group if 'poi' in item]
        if not pois: return []

        # Add connection lines between related POIs
        self._add_proximity_connections(folium_map, analyzed_pois_in_group)

        # Add POIs with group-specific styling
        self._add_group_pois(folium_map, analyzed_pois_in_group)

        # Add proximity analysis legend
        self._add_proximity_legend(folium_map)

        return pois

    def _add_proximity_connections(self, folium_map: folium.Map, analyzed_pois: List[Dict]) -> None:
        """Add visual connections between related POIs"""
        parent_poi = None
        connected_pois = []

        # Find parent and connected POIs
        for item in analyzed_pois:
            if item['link_status'] == 'Rodzic':
                parent_poi = item['poi']
            elif item['link_status'] == 'Polaczony':
                connected_pois.append(item['poi'])

        # Draw connections from parent to connected POIs
        if parent_poi and connected_pois:
            connection_group = folium.FeatureGroup(name='Proximity Connections', show=True)
            folium_map.add_child(connection_group)

            for connected_poi in connected_pois:
                folium.PolyLine(
                    locations=[
                        [parent_poi.location.y, parent_poi.location.x],
                        [connected_poi.location.y, connected_poi.location.x]
                    ],
                    color='blue',
                    weight=2,
                    opacity=0.5,
                    dash_array='5, 5'
                ).add_to(connection_group)

    def _add_group_pois(self, folium_map: folium.Map, analyzed_pois: List[Dict]) -> None:
        """Add POI markers with group status styling."""
        for item in analyzed_pois:
            poi = item['poi']
            status = item['link_status']
            icon_name, color = self._get_group_status_style(status)

            # Używamy `self.request` z klasy bazowej, aby przekazać go do helpera
            popup = PopupHelper.create_poi_popup(poi, self.request)
            tooltip = f"{poi.name} ({status})"

            icon = IconHelper.create_folium_icon(color, icon_name)
            folium.Marker(
                location=[poi.location.y, poi.location.x],
                popup=popup,
                tooltip=tooltip,
                icon=icon
            ).add_to(folium_map)

    def _add_proximity_legend(self, folium_map: folium.Map) -> None:
        """Add legend explaining proximity group symbols"""
        legend_html = """
        <div style="position: fixed; bottom: 10px; left: 10px; z-index: 1000; 
                    background: rgba(255,255,255,0.9); padding: 10px; 
                    border-radius: 5px; border: 1px solid #ccc; font-size: 12px;">
            <strong>Proximity Group Legend</strong><br/>
            <i class="fa fa-star" style="color: blue;"></i> Parent POI<br/>
            <i class="fa fa-link" style="color: green;"></i> Connected POI<br/>
            <i class="fa fa-unlink" style="color: red;"></i> Needs connection<br/>
        </div>
        """
        folium_map.get_root().html.add_child(folium.Element(legend_html))

    def _get_group_status_style(self, status: str) -> tuple:
        """Get icon and color for proximity group status"""
        status_mapping = {
            'Rodzic': ('star', 'blue'),
            'Polaczony': ('link', 'green'),
        }
        return status_mapping.get(status, ('unlink', 'red'))
