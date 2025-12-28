# odznaki/utils/map_utils/creators/badge_creator.py

import folium
from typing import List

from odznaki.models import PointOfInterest
from ..builders import MapBuilder


class BadgeMapCreator(MapBuilder):
    def _add_layers(self, folium_map: folium.Map, **kwargs) -> List[PointOfInterest]:
        badge = kwargs.get('badge')
        visited_poi_ids = kwargs.get('visited_poi_ids', set())

        # Tworzymy dwie osobne grupy/warstwy
        claimed_pois_group = folium.FeatureGroup(name='Zaliczone', show=True)
        unclaimed_pois_group = folium.FeatureGroup(name='Do Zdobycia', show=True)

        pois = list(badge.points_of_interest.all())

        for poi in pois:
            is_visited_for_this_badge = poi.id in visited_poi_ids

            # Używamy ogólnego statusu POI do kolorowania, ale logiki `is_visited`
            # do przypisania do grupy, co jest spójne.
            # Alternatywnie, możemy użyć prostszego statusu.
            # Użyjmy prostszej logiki: zielony/czerwony, tak jak poprzednio.
            status = 'zdobyty' if is_visited_for_this_badge else 'niezdobyty'

            marker = self.create_poi_marker(poi, status)

            # Decydujemy, do której grupy dodać znacznik
            if is_visited_for_this_badge:
                marker.add_to(claimed_pois_group)
            else:
                marker.add_to(unclaimed_pois_group)

        # Dodajemy obie grupy do mapy
        folium_map.add_child(claimed_pois_group)
        folium_map.add_child(unclaimed_pois_group)

        return pois
