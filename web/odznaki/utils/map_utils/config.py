# odznaki/utils/map_utils/config.py

from dataclasses import dataclass


@dataclass
class MapConfig:
    """Configuration constants for map creation"""
    DEFAULT_LOCATION = [52.2, 19.9]
    DEFAULT_ZOOM = 6
    VICINITY_DISTANCE_METERS = 1000
    VICINITY_ZOOM = 15
    AUDIT_ZOOM = 18
    SEGMENT_ZOOM = 13

    # Heat map settings
    HEATMAP_MIN_OPACITY = 0.3
    HEATMAP_RADIUS = 20
    HEATMAP_BLUR = 20

    # Boundary simplification (to reduce HTML size and render time)
    BOUNDARY_SIMPLIFY_TOLERANCE = 0.0003


# Style definitions
STATUS_COLORS = {
    'zdobyty': 'green',
    'do_ponowienia': 'blue',
    'niezdobyty': 'red',
    'nieaktywny': 'gray',
    'default': 'gray'
}

CATEGORY_ICONS = {
    'peak': ('icicles', 180),
    'tower': ('tower-observation', 0),
    'platform': ('explosion', 0),
    'shelter': ('house', 0),
    'cross': ('cross', 0),
    'lake': ('water', 0),
    'panorama': ('camera-retro', 0),
    'valley': ('hill-rockslide', 0),
    'waterfall': ('tint', 0),
    'cemetery': ('monument', 0),
    'building': ('building', 0),
    'pass': ('kip-sign', 270),
    'other': ('circle-info', 0),
    'default': ('info-circle', 0)
}


