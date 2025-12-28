# odznaki/urls.py
from django.urls import path
from . import views

app_name = 'odznaki'

urlpatterns = [
    # === GŁÓWNE WIDOKI ===
    path('', views.dashboard_view, name='dashboard'),
    path('search/', views.search_view, name='search'),
    path('timeline/', views.timeline_view, name='timeline'),

    # === ODZNAKI ===
    path('badges/', views.list_badges, name='badge-list'),
    path('badges/kanban/', views.badge_kanban_view, name='badge-kanban'),
    path('badge/<int:badge_id>/', views.badge_detail_view, name='badge-detail'),
    path('news/dismiss_multiple/', views.dismiss_multiple_news_items_view, name='dismiss-multiple-news-items'),

    # === PUNKTY TURYSTYCZNE (POI) ===
    path('pois/', views.poi_explorer_view, name='poi-explorer'),
    path('poi/<int:poi_id>/', views.poi_detail_view, name='poi-detail'),
    path('poi/<int:poi_id>/history/', views.poi_history_view, name='poi-history'),

    # === GEOGRAFIA ===
    path('geography/', views.geography_index_view, name='geography-index'),
    path('geography/region/<str:model_name>/<int:pk>/', views.geography_region_detail_view,
         name='geography-region-detail'),
    path('geography/range/<slug:range_slug>/', views.mountain_range_detail_view, name='mountain-range-detail'),
    path('geography/subregions/<str:parent_model_name>/<int:parent_id>/', views.get_subregions_json, name='get-subregions-json'),

    # === WYCIECZKI ===
    path('trips/', views.trip_list_view, name='trip-list'),
    path('trip/<int:trip_id>/', views.trip_detail_view, name='trip-detail'),

    # === ORGANIZATORZY I KSIĄŻECZKI ===
    path('organizers/', views.organizer_list_view, name='organizer-list'),
    path('organizer/<int:pk>/', views.organizer_detail_view, name='organizer-detail'),
    path('booklets/', views.booklet_list_view, name='booklet-list'),
    path('booklet/<int:pk>/', views.booklet_detail_view, name='booklet-detail'),

    # === ANALITYKA I RANKINGI ===
    path('analytics/activity/', views.mesoregion_activity_view, name='analytics-activity'),
    path('analytics/yearly/', views.yearly_stats_view, name='analytics-yearly'),  # <-- NOWA ŚCIEŻKA
    path('analytics/gpx-heatmap/', views.gpx_heatmap_view, name='analytics-gpx-heatmap'),
    path('analytics/profile/', views.profile_stats_view, name='analytics-profile'),
    path('scores/poi/', views.poi_scores_view, name='poi-scores'),
    path('scores/region/', views.mesoregion_scores_view, name='mesoregion-scores'),

    # === NARZĘDZIA ===
    path('tools/proximity/', views.proximity_tool_view, name='tool-poi-proximity'),
    path('tools/proximity-map/', views.proximity_group_map_view, name='tool-proximity-map'),
    path('tools/geo-audit/', views.geo_audit_view, name='tool-geo-audit'),
    path('tools/asset-audit/', views.asset_audit_view, name='tool-asset-audit'),
    path('tools/potential-visits/', views.potential_visits_finder_view, name='tool-potential-visits'),
    path('tools/create-visit-from-suggestion/', views.create_visit_from_suggestion_view,
         name='create-visit-from-suggestion'),
    path('tools/orphaned-pois/', views.orphaned_pois_auditor_view, name='tool-orphaned-pois'),
    path('tools/map-settings/', views.map_settings_view, name='tool-map-settings'),
    path('tools/missing-coordinates/', views.missing_coordinates_audit_view, name='tool-missing-coordinates'),

]