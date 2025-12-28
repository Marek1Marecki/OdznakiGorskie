# odznaki/utils/map_utils/layer_manager.py

from django.conf import settings


def get_all_available_map_layers():
    """
    Zwraca "surową" listę wszystkich potencjalnie dostępnych warstw.
    Cała logika (wstrzykiwanie kluczy API, filtrowanie) znajduje się w `map_utils/config.py`.
    Wszystkie URL-e używają pojedynczych nawiasów klamrowych.
    """
    return [
        {
            'id': 'osm_standard',
            'name': 'OpenStreetMap (Standard)',
            'tiles': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            'attr': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            'is_paid': False,
            'is_base': True,
        },
        {
            'id': 'opentopomap',
            'name': 'OpenTopoMap (Topograficzna)',
            'tiles': 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
            'attr': 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)',
            'is_paid': False,
            'is_base': False,
        },
        {
            'id': 'esri_satellite',
            'name': 'Esri Satellite (Satelitarna)',
            'tiles': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            'attr': 'Tiles &copy; Esri',
            'is_paid': False,
            'is_base': False,
        },
        {
            'id': 'esri_topo',
            'name': 'Esri Topo (Stonowana)',
            'tiles': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
            'attr': 'Tiles &copy; Esri',
            'is_paid': False,
            'is_base': False,
        },
        {
            'id': 'cartodb_positron',
            'name': 'CartoDB Positron (Minimalistyczna)',
            'tiles': 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
            'attr': '&copy; OpenStreetMap contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            'is_paid': False,
            'is_base': False,
        },
        {
            'id': 'mtb_map',
            'name': 'MTB Map (Szlaki Rowerowe)',
            'tiles': 'https://tile.mtbmap.cz/mtbmap_tiles/{z}/{x}/{y}.png',
            'attr': '&copy; OpenStreetMap contributors &amp; <a href="https://www.mtbmap.cz">MTBmap.cz</a>',
            'is_paid': False,
            'is_base': False,
        },
        {
            'id': 'cyclosm',
            'name': 'CyclOSM (Poziomice i Szlaki)',
            'tiles': 'https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png',
            'attr': '<a href="https://github.com/cyclosm/cyclosm-cartocss-style/releases" title="CyclOSM - Open Bicycle render">CyclOSM</a> | Map data: &copy; OpenStreetMap contributors',
            'is_paid': False,
            'is_base': False,
        },
        {
            'id': 'mapycz_outdoor',
            'name': 'Mapy.cz (Turystyczna)',
            'tiles': 'https://api.mapy.cz/v1/maptiles/outdoor/256/{z}/{x}/{y}?apikey={api_key}',
            'attr': '<a href="https://api.mapy.cz/copyright" target="_blank">&copy; Seznam.cz a.s. a další</a>',
            'is_paid': True,
            'is_base': False,
        },
    ]


def get_map_layers(request):
    """
    Dynamicznie buduje listę AKTYWNYCH warstw mapy.
    To jest JEDYNE miejsce, gdzie wstrzykiwane są klucze API.
    """
    from django.core.cache import cache

    active_layer_ids = cache.get('active_map_layers', ['osm_standard'])
    all_available_layers = get_all_available_map_layers()
    mapycz_api_key = getattr(settings, 'MAPY_CZ_API_KEY', None)

    final_layers = []
    is_first_active = True
    for layer_config in all_available_layers:
        if layer_config['id'] in active_layer_ids:
            new_layer = layer_config.copy()

            # --- ULEPSZONA, ELASTYCZNA LOGIKA WSTRZYKIWANIA KLUCZY ---
            if '{mapycz_api_key}' in new_layer['tiles']:
                if mapycz_api_key:
                    new_layer['tiles'] = new_layer['tiles'].replace('{mapycz_api_key}', mapycz_api_key)
                else:
                    continue  # Pomiń warstwę, jeśli wymaga klucza, a go nie ma

            new_layer['show'] = is_first_active
            is_first_active = False
            final_layers.append(new_layer)

    # Fallback
    if not final_layers:
        base_osm = next((l for l in all_available_layers if l.get('is_base')), all_available_layers[0]).copy()
        base_osm['show'] = True
        final_layers.append(base_osm)

    return final_layers
