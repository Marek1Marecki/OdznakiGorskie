# odznaki/utils/map_utils/creators/segment_preview_creator.py

import folium
from typing import List, Optional
from ..builders import MapBuilder
from ..config import MapConfig


class SegmentPreviewMapCreator(MapBuilder):
    """Creator for single segment preview maps"""

    def __init__(self, request, segment=None):
        """
        Initialize creator with segment-specific configuration.

        Args:
            request: Django HttpRequest object
            segment: TripSegment object to preview
        """
        # Calculate center location from segment if available
        location = self._calculate_segment_center(segment) if segment else None

        super().__init__(
            request=request,
            location=location,
            zoom=MapConfig.SEGMENT_ZOOM
        )

    def _calculate_segment_center(self, segment) -> Optional[List[float]]:
        """Calculate center point of segment for map centering"""
        if not segment or not segment.gpx_path:
            return None

        try:
            bounds = segment.gpx_path.extent
            center_lat = (bounds[1] + bounds[3]) / 2  # (min_lat + max_lat) / 2
            center_lon = (bounds[0] + bounds[2]) / 2  # (min_lon + max_lon) / 2
            return [center_lat, center_lon]
        except Exception:
            return None

    def _add_layers(self, folium_map: folium.Map, **kwargs) -> List:
        """
        Add segment path to the map.

        Args:
            folium_map: Folium map instance
            **kwargs: Must contain 'segment' key with TripSegment object

        Returns:
            List containing the segment for bounds fitting
        """
        segment = kwargs.get('segment')

        if not segment or not segment.gpx_path:
            return []

        # Add the segment path with styling from the model
        self._add_segment_path(folium_map, segment)

        return [segment]

    def _add_segment_path(self, folium_map: folium.Map, segment) -> None:
        """
        Add segment GPX path to the map with model-defined styling.

        Args:
            folium_map: Folium map instance
            segment: TripSegment object with gpx_path and styling properties
        """

        # Create style function using segment properties
        def style_function(feature):
            style = {
                'color': getattr(segment, 'color', '#3388ff'),
                'weight': getattr(segment, 'weight', 3),
                'opacity': 0.9
            }

            # Add dash array if defined
            dash_array = getattr(segment, 'dash_array', None)
            if dash_array:
                style['dashArray'] = dash_array

            return style

        # Add GeoJSON layer with segment styling
        folium.GeoJson(
            segment.gpx_path.json,
            name='Trasa GPX',
            style_function=style_function,
            tooltip=self._create_segment_tooltip(segment),
            popup=self._create_segment_popup(segment)
        ).add_to(folium_map)

    def _create_segment_tooltip(self, segment) -> str:
        """Create simple tooltip for segment hover"""
        sequence = getattr(segment, 'sequence', 'N/A')
        return f"Segment {sequence}"

    def _create_segment_popup(self, segment) -> folium.Popup:
        """Create detailed popup for segment click"""
        html_content = self._build_segment_popup_html(segment)
        return folium.Popup(html_content, max_width=300)

    def _build_segment_popup_html(self, segment) -> str:
        """Build HTML content for segment popup"""
        sequence = getattr(segment, 'sequence', 'N/A')
        html = f"<div style='font-family: sans-serif;'>"
        html += f"<strong>Segment {sequence}</strong><br/>"

        # Add start/end points if available
        start_point = getattr(segment, 'start_point_name', None)
        end_point = getattr(segment, 'end_point_name', None)

        if start_point:
            html += f"<strong>Start:</strong> {start_point}<br/>"
        if end_point:
            html += f"<strong>End:</strong> {end_point}<br/>"

        # Add distance if available
        distance = getattr(segment, 'distance', None)
        if distance:
            html += f"<strong>Distance:</strong> {distance:.1f} km<br/>"

        # Add elevation gain if available
        elevation_gain = getattr(segment, 'elevation_gain', None)
        if elevation_gain:
            html += f"<strong>Elevation gain:</strong> {elevation_gain} m<br/>"

        # Add description if available
        description = getattr(segment, 'description', None)
        if description:
            html += f"<strong>Description:</strong><br/>{description}<br/>"

        html += "</div>"
        return html

    def create_base_map(self) -> folium.Map:
        """
        Create base map optimized for segment preview.

        Override parent method to skip MiniMap for small previews.
        """
        m = folium.Map(
            location=self.location,
            zoom_start=self.zoom,
            tiles=None,
            control_scale=True  # Keep scale for reference
        )

        # Add base tile layers
        self._add_base_layers(m)

        # Skip MiniMap for preview maps to save space
        # Skip layer control for simple previews

        return m

    def _finalize_map(self, folium_map: folium.Map, objects: list = None):
        """
        Finalize map with bounds fitting.

        Override to skip layer control for simple preview maps.
        """
        # Fit bounds to segment
        self._fit_bounds_to_segment(folium_map, objects)

    def _fit_bounds_to_segment(self, folium_map: folium.Map, objects: list = None):
        """
        Fit map bounds to segment extent.

        Args:
            folium_map: Folium map instance
            objects: List of objects (should contain segment)
        """
        if not objects:
            return

        segment = objects[0] if objects else None
        if not segment or not hasattr(segment, 'gpx_path') or not segment.gpx_path:
            # Fallback to default location/zoom
            folium_map.location = self.location
            folium_map.zoom_start = self.zoom
            return

        try:
            bounds = segment.gpx_path.extent
            # Convert bounds to folium format: [[min_lat, min_lon], [max_lat, max_lon]]
            folium_bounds = [
                [bounds[1], bounds[0]],  # [min_lat, min_lon]
                [bounds[3], bounds[2]]  # [max_lat, max_lon]
            ]
            folium_map.fit_bounds(folium_bounds, padding=(10, 10))
        except Exception:
            # Fallback if bounds calculation fails
            folium_map.location = self.location
            folium_map.zoom_start = self.zoom


def create_segment_preview_map(segment, request=None):
    """
    Compatibility function that matches the original API.

    Args:
        segment: TripSegment object to preview
        request: Django HttpRequest (optional, can be None for previews)

    Returns:
        folium.Map or None if segment has no gpx_path
    """
    if not segment or not getattr(segment, 'gpx_path', None):
        return None

    # Use a mock request if none provided (for backward compatibility)
    if request is None:
        from unittest.mock import Mock
        request = Mock()
        request.build_absolute_uri = lambda x: x

    creator = SegmentPreviewMapCreator(request=request, segment=segment)
    return creator.build(segment=segment)
