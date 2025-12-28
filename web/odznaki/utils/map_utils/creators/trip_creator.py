# odznaki/utils/map_utils/creators/trip_creator.py

import folium
from typing import List, Dict, Any


from odznaki.services.point_of_interest_service import calculate_poi_statuses
from ..builders import MapBuilder


class TripMapCreator(MapBuilder):
    """Creator for trip detail maps with routes and POIs"""

    def _add_layers(self, folium_map: folium.Map, **kwargs):
        trip = kwargs.get('trip')
        nearby_pois_qs = kwargs.get('nearby_pois_qs')
        if not trip: return []

        # --- ZMIANA LOGIKI: NAJPIERW ZBIERAMY DANE, POTEM RYSUJEMY ---
        # 1. Zbierz wszystkie segmenty i ich koordynaty w poprawnej kolejności
        segments_with_paths = list(trip.gpx_paths.exclude(gpx_path__isnull=True).order_by('sequence'))
        all_trip_coords = []
        for segment in segments_with_paths:
            all_trip_coords.extend(segment.gpx_path.coords)

        # 2. Rysuj segmenty trasy (bez zmian)
        self._add_trip_segments_paths(folium_map, segments_with_paths)

        # 3. Rysuj znaczniki TYLKO dla globalnego startu i mety
        if all_trip_coords:
            self._add_global_start_end_markers(folium_map, trip, all_trip_coords)

        # 4. Dodaj pobliskie POI (bez zmian)
        if nearby_pois_qs and nearby_pois_qs.exists():
            self._add_trip_pois(folium_map, nearby_pois_qs)

        # Zwróć obiekty do dopasowania granic (bez zmian)
        objects_for_bounds = list(segments_with_paths)
        if nearby_pois_qs and nearby_pois_qs.exists():
            objects_for_bounds.extend(list(nearby_pois_qs))
        return objects_for_bounds

    def _add_trip_segments_paths(self, folium_map: folium.Map, segments: List) -> None:
        """Rysuje tylko linie (PolyLine) dla każdego segmentu."""
        segment_group = folium.FeatureGroup(name='Trasa Wycieczki', show=True)
        folium_map.add_child(segment_group)

        for segment in segments:
            locations = [(lat, lon) for lon, lat, *_ in segment.gpx_path.coords]
            tooltip_text = self._create_segment_tooltip(segment)

            folium.PolyLine(
                locations=locations,
                color=segment.color,
                weight=segment.weight,
                opacity=0.9,
                dash_array=segment.dash_array if segment.dash_array else None,
                tooltip=tooltip_text,
                popup=folium.Popup(self._create_segment_popup(segment), max_width=300)
            ).add_to(segment_group)

    def _add_global_start_end_markers(self, folium_map: folium.Map, trip, all_coords: List) -> None:
        """Dodaje znaczniki tylko dla początku i końca całej wycieczki."""
        marker_group = folium.FeatureGroup(name='Start / Meta', show=True)
        folium_map.add_child(marker_group)

        # Znacznik Startu (zielone kółko)
        start_coords = all_coords[0]
        folium.CircleMarker(
            location=[start_coords[1], start_coords[0]],  # (lat, lon)
            radius=8,  # Większy promień, żeby było widoczne
            color='green',
            fill=True,
            fill_color='green',
            fill_opacity=0.8,
            popup=f"Start: {trip.start_point_name}",
            tooltip="Początek wycieczki"
        ).add_to(marker_group)

        # Znacznik Mety (czerwone kółko)
        end_coords = all_coords[-1]
        folium.CircleMarker(
            location=[end_coords[1], end_coords[0]],  # (lat, lon)
            radius=8,
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.8,
            popup=f"Meta: {trip.end_point_name}",
            tooltip="Koniec wycieczki"
        ).add_to(marker_group)

    def _add_trip_pois(self, folium_map: folium.Map, nearby_pois_qs) -> None:
        """Add POI markers with trip-specific styling"""
        poi_statuses = calculate_poi_statuses(nearby_pois_qs)
        poi_group = folium.FeatureGroup(name='Pobliskie POI', show=True)
        folium_map.add_child(poi_group)

        for poi in nearby_pois_qs:
            status = poi_statuses.get(poi.id, 'default')

            # `all_points_for_bounds` nie jest już tutaj potrzebne

            tooltip = f"POI: {poi.name} | Status: {status}"
            marker = self.create_poi_marker(poi, status, custom_tooltip=tooltip)
            marker.add_to(poi_group)

    def _create_segment_tooltip(self, segment) -> str:
        """Create informative tooltip for segment"""
        return f"Segment {segment.sequence}: {segment.start_point_name} → {segment.end_point_name}"

    def _create_segment_popup(self, segment) -> str:
        """Create detailed popup for segment"""
        popup_html = f"""
        <strong>Segment {segment.sequence}</strong><br/>
        <strong>From:</strong> {segment.start_point_name}<br/>
        <strong>To:</strong> {segment.end_point_name}<br/>
        """
        if hasattr(segment, 'distance') and segment.distance:
            popup_html += f"<strong>Distance:</strong> {segment.distance:.1f} km<br/>"
        if hasattr(segment, 'elevation_gain') and segment.elevation_gain:
            popup_html += f"<strong>Elevation gain:</strong> {segment.elevation_gain} m<br/>"
        return popup_html





'''
    def _add_trip_segments(self, folium_map: folium.Map, trip, all_points_for_bounds: List) -> None:
        """Add trip segments with enhanced styling and tooltips"""
        segment_group = folium.FeatureGroup(name='Trip Route', show=True)
        folium_map.add_child(segment_group)

        for segment in trip.gpx_paths.all():
            if segment.gpx_path:
                locations = [(lat, lon) for lon, lat, *_ in segment.gpx_path.coords]
                all_points_for_bounds.extend(locations)

                # Enhanced tooltip with segment statistics
                tooltip_text = self._create_segment_tooltip(segment)

                folium.PolyLine(
                    locations=locations,
                    color=segment.color,
                    weight=segment.weight,
                    opacity=0.9,
                    dash_array=segment.dash_array if segment.dash_array else None,
                    tooltip=tooltip_text,
                    popup=folium.Popup(self._create_segment_popup(segment), max_width=300)
                ).add_to(segment_group)

                # Add start/end markers for segments
                if locations:
                    self._add_segment_endpoints(segment_group, segment, locations)
'''




class TripPreviewMapCreator(MapBuilder):
    """
    Kreator mapy podglądowej dla wycieczki, zgodny z architekturą MapBuilder.
    """

    def _add_layers(self, folium_map: folium.Map, **kwargs) -> List:
        """
        Implementuje wymaganą metodę: dodaje wszystkie segmenty trasy do mapy.
        """
        trip = kwargs.get('trip')
        if not trip:
            return []

        segments_with_paths = trip.gpx_paths.exclude(gpx_path__isnull=True).order_by('sequence')

        if not segments_with_paths.exists():
            return []

        # Dodajemy segmenty z uproszczonym stylem
        for segment in segments_with_paths:
            folium.GeoJson(
                segment.gpx_path.json,
                name=f"Segment {segment.sequence}",
                style_function=lambda x, color=segment.color, weight=max(2, segment.weight - 1): {
                    'color': color,
                    'weight': weight,
                    'opacity': 0.7
                },
                tooltip=f"Segment {segment.sequence}"
            ).add_to(folium_map)

        # Zwracamy listę segmentów, aby metoda _fit_bounds mogła dopasować do nich widok
        return list(segments_with_paths)
