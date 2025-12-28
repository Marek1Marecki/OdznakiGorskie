# odznaki/views/__init__.py

# === WIDOKI GŁÓWNE I NAWIGACYJNE ===
from .dashboard_views import dashboard_view, dismiss_multiple_news_items_view
from .search_view import search_view
from .timeline_view import timeline_view

# === ODZNAKI I POI ===
from .badge_list_views import list_badges
from .badge_kanban_view import badge_kanban_view
from .badge_detail_views import badge_detail_view
from .poi_detail_views import poi_detail_view
from .poi_history_view import poi_history_view
from .poi_explorer_views import poi_explorer_view

# === GEOGRAFIA ===
from .geography_views import (
    geography_index_view,
    geography_region_detail_view,
    mountain_range_detail_view,
    get_subregions_json
)

# === WYCIECZKI ===
from .trip_list_view import trip_list_view
from .trip_detail_view import trip_detail_view

# === ORGANIZATORZY I KSIĄŻECZKI ===
from .organizer_views import organizer_list_view, organizer_detail_view
from .booklet_views import booklet_list_view, booklet_detail_view

# === ANALITYKA I RANKINGI ===
from .analytics_views import mesoregion_activity_view, yearly_stats_view, gpx_heatmap_view, profile_stats_view
from .scoring_views import poi_scores_view, mesoregion_scores_view

# === NARZĘDZIA ===
from .tools.asset_audit_view import asset_audit_view
from .tools.geo_audit_view import geo_audit_view
from .tools.orphaned_pois_view import orphaned_pois_auditor_view
from .tools.poi_proximity_view import proximity_tool_view
from .tools.proximity_map_view import proximity_group_map_view
from .tools.potential_visits_view import (
    potential_visits_finder_view,
    create_visit_from_suggestion_view
)
from .tools.settings_views import map_settings_view
from .tools.data_audit_views import missing_coordinates_audit_view


# === OBSŁUGA BŁĘDÓW ===
# (Te są zwykle importowane bezpośrednio w urls.py, ale dla kompletności można je tu mieć)
# from .error_views import handler404, handler500