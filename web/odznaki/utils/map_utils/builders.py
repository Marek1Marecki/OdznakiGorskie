# odznaki/utils/map_utils/builders.py

# --- Standard Library Imports ---
from dataclasses import dataclass
from typing import List, Optional, Tuple

# --- Third-Party Imports ---
import folium
from folium.plugins import MiniMap

# --- Django Imports ---
from django.urls import reverse

# --- Application-Specific Imports ---
from odznaki.models import PointOfInterest
# Importujemy naszą nową, czystą konfigurację
from .config import MapConfig, STATUS_COLORS, CATEGORY_ICONS
from .layer_manager import get_map_layers


@dataclass
class MarkerData:
    """Data structure for marker creation"""
    location: Tuple[float, float]
    popup_html: str
    tooltip: str
    color: str
    icon_name: str
    icon_angle: int = 0


class IconHelper:
    """Helper class for icon management"""

    @staticmethod
    def get_icon_info(category: str) -> Tuple[str, int]:
        """Get icon name and angle for a category"""
        icon_info = CATEGORY_ICONS.get(category, CATEGORY_ICONS['default'])
        if isinstance(icon_info, tuple):
            return icon_info
        return icon_info, 0

    @staticmethod
    def create_folium_icon(color: str, icon_name: str, icon_angle: int = 0) -> folium.Icon:
        """Create a Folium icon with specified parameters"""
        return folium.Icon(
            prefix='fa',
            color=color,
            icon=icon_name,
            angle=icon_angle
        )


class PopupHelper:
    """
    Centralna klasa do tworzenia ustandaryzowanych dymków (popup) Folium.
    """

    @staticmethod
    def _build_url(request, view_name: str, kwargs: dict) -> str:
        """Buduje pełny, absolutny URL."""
        relative_url = reverse(view_name, kwargs=kwargs)
        # Używamy `request` jeśli jest dostępne, w przeciwnym razie tworzymy względny URL
        if request:
            return request.build_absolute_uri(relative_url)
        return relative_url

    @staticmethod
    def create_poi_popup(poi: PointOfInterest, request) -> folium.Popup:
        """Tworzy popup dla PointOfInterest z klikalnymi linkami."""
        poi_url = PopupHelper._build_url(request, 'odznaki:poi-detail', {'poi_id': poi.id})

        html = f"<strong><a href='{poi_url}' target='_top' class='app-link'>{poi.name}</a></strong>"

        if poi.height:
            html += f"<br/>Wysokość: {poi.height} m n.p.m."

        # --- ZMIANA JEST TUTAJ ---
        if poi.mesoregion:
            region_url = PopupHelper._build_url(
                request,
                'odznaki:geography-region-detail',
                {'model_name': 'mesoregion', 'pk': poi.mesoregion.pk}
            )
            # Tworzymy link do mezoregionu
            html += f"<br/>Region: <a href='{region_url}' target='_top' class='app-link'>{poi.mesoregion.name}</a>"
        # --- KONIEC ZMIANY ---

        return folium.Popup(html, max_width=250)

    @staticmethod
    def create_neighbor_popup(region, request) -> folium.Popup:
        """Tworzy popup dla sąsiadującego regionu."""
        url = PopupHelper._build_url(
            request,
            'odznaki:geography-region-detail',
            {'model_name': region._meta.model_name, 'pk': region.pk}
        )
        html = f"""
            <div style="font-family: sans-serif;">
                <strong>Sąsiad:</strong><br>{region.name}<br><br>
                <a href="{url}" target="_top" class="folium-popup-button">Przejdź do regionu</a>
            </div>
            <style>.folium-popup-button {{ 
                padding: 5px 10px; border: 1px solid #ccc; border-radius: 4px; 
                text-decoration: none; color: black; 
            }}</style>
        """
        return folium.Popup(html, max_width=250)


class MapBuilder:
    """
    Główna klasa bazowa do budowania map z użyciem wzorca Metody Szablonowej.
    """

    def __init__(self, request, location: Optional[List[float]] = None, zoom: Optional[int] = None):
        self.request = request
        self.config = MapConfig()
        self.location = location or self.config.DEFAULT_LOCATION
        self.zoom = zoom or self.config.DEFAULT_ZOOM

    def build(self, **kwargs) -> folium.Map:
        """
        Główna metoda budująca mapę (Metoda Szablonowa).
        Definiuje szkielet algorytmu tworzenia mapy.
        """
        m = self.create_base_map()
        objects_for_bounds = self._add_layers(m, **kwargs)
        self._finalize_map(m, objects=objects_for_bounds)
        return m

    def _add_layers(self, folium_map: folium.Map, **kwargs):
        """
        Metoda abstrakcyjna. Każda podklasa musi ją zaimplementować.
        To tutaj dodawane są specyficzne warstwy (znaczniki, trasy, kontury).
        """
        raise NotImplementedError("Podklasy MapBuilder muszą implementować _add_layers()")

    def _finalize_map(self, folium_map: folium.Map, objects: list = None):
        """
        Dodaje końcowe, wspólne elementy do mapy, takie jak kontrolki
        i dopasowanie widoku.
        """
        # 1. Dodaj przełącznik warstw
        self.add_controls(folium_map)
        self._fit_bounds(folium_map, objects=objects)

    def _fit_bounds(self, folium_map: folium.Map, objects: Optional[list] = None, padding: tuple = (20, 20)):
        """
        Uniwersalna metoda do dopasowywania granic mapy.
        """
        bounds = []
        if objects:
            for obj in objects:
                geom = getattr(obj, 'location', None) or getattr(obj, 'gpx_path', None) or getattr(obj, 'shape', None)
                if geom:
                    min_lon, min_lat, max_lon, max_lat = geom.extent
                    bounds.extend([[min_lat, min_lon], [max_lat, max_lon]])

        if bounds:
            folium_map.fit_bounds(bounds, padding=padding)
        else:
            folium_map.location = self.location
            folium_map.zoom_start = self.zoom

    def create_base_map(self) -> folium.Map:
        """Create a base map with standard configuration"""
        m = folium.Map(
            location=self.location,
            zoom_start=self.zoom,
            tiles=None,
            control_scale=True
        )
        self._add_base_layers(m)
        self._add_minimap(m)
        return m

    def _add_base_layers(self, folium_map: folium.Map) -> None:
        """Add base tile layers to the map"""
        active_layers = get_map_layers(self.request)
        for layer in active_layers:
            folium.TileLayer(
                tiles=layer['tiles'],
                attr=layer['attr'],
                name=layer['name'],
                control=True,
                show=layer['show'],
            ).add_to(folium_map)

    def _add_minimap(self, folium_map: folium.Map) -> None:
        """Add minimap to the bottom right corner"""
        try:
            mini_map = MiniMap(position='bottomright', toggle_display=True)
            mini_map.add_to(folium_map)
        except Exception:
            # Silent fallback if MiniMap fails
            pass

    def add_controls(self, folium_map: folium.Map) -> None:
        """Add layer control to the map"""
        # Check if control already exists
        for child in folium_map._children.values():
            if isinstance(child, folium.LayerControl):
                return

        folium.LayerControl(position='topright', collapsed=True).add_to(folium_map)

    # Upraszczamy `create_poi_marker`, wchłaniając `_prepare_marker_data`
    def create_poi_marker(self, poi: PointOfInterest, status: str, custom_tooltip: str = None) -> folium.Marker:
        """Tworzy ustandaryzowany znacznik POI, używając PopupHelper."""
        color = STATUS_COLORS.get(status, STATUS_COLORS['default'])
        icon_name, icon_angle = IconHelper.get_icon_info(poi.category)
        icon = IconHelper.create_folium_icon(color, icon_name, icon_angle)

        # Używamy naszego nowego, centralnego helpera do popupów
        popup = PopupHelper.create_poi_popup(poi, self.request)
        tooltip = custom_tooltip or poi.name

        return folium.Marker(location=[poi.location.y, poi.location.x], popup=popup, tooltip=tooltip, icon=icon)
