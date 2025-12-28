import folium
from collections import defaultdict
from datetime import date

from odznaki.models import BadgeRequirement, Visit
from ..builders import MapBuilder


class OrganizerMapCreator(MapBuilder):
    def _add_layers(self, folium_map: folium.Map, **kwargs):
        poi_queryset = kwargs.get('poi_queryset')
        badges_context_qs = kwargs.get('badges_context_qs')

        if not poi_queryset or not poi_queryset.exists():
            return []

        poi_list = list(poi_queryset)
        poi_ids = [p.id for p in poi_list]
        today = date.today()

        visits_data = defaultdict(list)
        for v in Visit.objects.filter(point_of_interest_id__in=poi_ids).values('point_of_interest_id', 'visit_date'):
            visits_data[v['point_of_interest_id']].append(v['visit_date'])

        reqs_data = defaultdict(list)
        if badges_context_qs:
            reqs_qs = BadgeRequirement.objects.filter(
                point_of_interest_id__in=poi_ids,
                badge__in=badges_context_qs
            ).values(
                'point_of_interest_id',
                'badge__start_date',
                'badge__end_date'
            )
            for r in reqs_qs:
                reqs_data[r['point_of_interest_id']].append(r)

        poi_statuses = {}
        for poi in poi_list:
            badges_for_this_poi = reqs_data.get(poi.id, [])
            visits_for_this_poi = visits_data.get(poi.id, [])

            if not badges_for_this_poi:
                poi_statuses[poi.id] = 'nieaktywny'
                continue

            all_requirements_met = True
            for badge_req in badges_for_this_poi:
                is_claimed_for_this_badge = any(
                    (not badge_req['badge__start_date'] or v >= badge_req['badge__start_date']) and
                    (not badge_req['badge__end_date'] or v <= badge_req['badge__end_date'])
                    for v in visits_for_this_poi
                )
                if not is_claimed_for_this_badge:
                    all_requirements_met = False
                    break

            if all_requirements_met:
                poi_statuses[poi.id] = 'zdobyty'
            else:
                poi_statuses[poi.id] = 'niezdobyty'

        visited_pois_group = folium.FeatureGroup(name='POI Zdobyte (w kontekście)', show=True)
        tovisit_pois_group = folium.FeatureGroup(name='POI Do Zdobycia (w kontekście)', show=True)

        for poi in poi_list:
            status = poi_statuses.get(poi.id, 'default')
            marker = self.create_poi_marker(poi, status)

            if status == 'zdobyty':
                marker.add_to(visited_pois_group)
            else:
                marker.add_to(tovisit_pois_group)

        folium_map.add_child(visited_pois_group)
        folium_map.add_child(tovisit_pois_group)

        return poi_list