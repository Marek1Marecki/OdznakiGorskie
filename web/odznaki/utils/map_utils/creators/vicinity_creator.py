# odznaki/utils/map_utils/creators/vicinity_creator.py

import folium
from typing import List

from django.contrib.gis.db.models.functions import Transform
from django.db.models import Prefetch

from odznaki.models import PointOfInterest, BadgeRequirement, Visit
from odznaki.services.point_of_interest_service import calculate_poi_statuses
from ..builders import MapBuilder, IconHelper, PopupHelper
from ..config import MapConfig, STATUS_COLORS


class VicinityMapCreator(MapBuilder):
    """Creator for POI vicinity maps"""

    def __init__(self, request, main_poi: PointOfInterest):
        # Ustawiamy centrum i zoom specyficzne dla tej mapy
        super().__init__(
            request,
            location=[main_poi.location.y, main_poi.location.x] if main_poi.location else None,
            zoom=MapConfig.VICINITY_ZOOM
        )

    def _add_layers(self, folium_map: folium.Map, **kwargs) -> List[PointOfInterest]:
        main_poi = kwargs.get('main_poi')
        if not main_poi or not main_poi.location:
            return []

        main_poi_location_metric = main_poi.location.transform(3857, clone=True)

        # --- ZMIANA JEST TUTAJ ---

        # 1. Budujemy QuerySet, zamiast od razu materializować listę
        nearby_pois_qs = PointOfInterest.objects.annotate(
            location_metric=Transform('location', 3857)
        ).filter(
            location_metric__dwithin=(main_poi_location_metric, self.config.VICINITY_DISTANCE_METERS)
        )

        # 2. Dodajemy prefetch_related, aby dociągnąć wszystkie potrzebne dane
        #    w minimalnej liczbie zapytań.
        nearby_pois_with_data = list(
            nearby_pois_qs.prefetch_related(
                'visits',
                Prefetch(
                    'badge_requirements',
                    queryset=BadgeRequirement.objects.select_related('badge')
                )
            )
        )

        # --- KONIEC ZMIANY ---

        # Przekazujemy do kalkulatora QuerySet, który ma już "w sobie" wszystkie dane
        poi_statuses = calculate_poi_statuses(nearby_pois_with_data)

        for poi in nearby_pois_with_data:
            status = poi_statuses.get(poi.id, 'default')
            if poi.id == main_poi.id:
                # Wyróżniamy główny punkt POI

                # --- DROBNA POPRAWKA: Używamy poprawnego koloru statusu dla gwiazdki ---
                main_poi_color = STATUS_COLORS.get(status, 'red')
                icon = IconHelper.create_folium_icon(main_poi_color, 'star')
                # --- KONIEC POPRAWKI ---

                popup = PopupHelper.create_poi_popup(poi, self.request)
                folium.Marker(
                    location=[poi.location.y, poi.location.x],
                    popup=popup,
                    tooltip=f"Główny cel: {poi.name}",
                    icon=icon
                ).add_to(folium_map)
            else:
                marker = self.create_poi_marker(poi, status)
                marker.add_to(folium_map)

        return nearby_pois_with_data
