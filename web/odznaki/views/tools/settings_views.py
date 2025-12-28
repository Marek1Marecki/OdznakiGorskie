# odznaki/views/tools/settings_views.py

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.core.cache import cache
from odznaki.utils.map_utils.layer_manager import get_all_available_map_layers


def map_settings_view(request):
    """
    Widok do zarządzania aktywnymi warstwami map.
    Wersja 2.0: Poprawnie obsługuje POST po refaktoryzacji.
    """

    # --- POBIERZ PEŁNĄ LISTĘ WARSTW RAZ, NA POCZĄTKU ---
    all_layers = get_all_available_map_layers()

    if request.method == 'POST':
        selected_layer_ids = request.POST.getlist('active_layers')

        # Używamy teraz `all_layers`, którą pobraliśmy na początku
        base_layer_id = next((layer['id'] for layer in all_layers if layer.get('is_base')), None)
        if base_layer_id and base_layer_id not in selected_layer_ids:
            selected_layer_ids.insert(0, base_layer_id)

        cache.set('active_map_layers', selected_layer_ids, timeout=None)

        messages.success(request, "Ustawienia warstw mapy zostały pomyślnie zapisane.")
        return redirect(reverse('odznaki:tool-map-settings'))

    # --- LOGIKA WYŚWIETLANIA FORMULARZA (GET) ---
    active_layer_ids = cache.get('active_map_layers', ['osm_standard'])

    context = {
        'all_layers': all_layers,
        'active_layer_ids': active_layer_ids,
    }
    return render(request, 'odznaki/tools/map_settings.html', context)
