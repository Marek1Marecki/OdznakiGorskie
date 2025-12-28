# odznaki/views/tools/asset_audit_view.py
from django.shortcuts import render
# ZMIANA: Importujemy serwis bezpośrednio
from odznaki.services import asset_audit_service

# Definicja opcji pozostaje bez zmian
SCAN_OPTIONS = {
    'badge_level': "Stopnie Odznak (obrazki)",
    'booklet_image': "Książeczki (okładki)",
    'booklet_scan': "Książeczki (skany PDF)",
    'organizer': "Organizatorzy (odznaki klubowe)",
    'poi_photo': "Zdjęcia Punktów POI",
    'trip_segment': "Segmenty Wycieczek (pliki GPX)",
}

def asset_audit_view(request):
    """
    Widok dla narzędzia do audytu integralności plików.
    Obsługuje wyświetlanie formularza i wyników audytu.
    """
    context = {
        'scan_options': SCAN_OPTIONS,
        'audit_results': None,
        'selected_options': [],
        'total_problems_count': 0,
    }

    if request.method == 'POST':
        # Pobieramy listę zaznaczonych checkboxów
        selected_options = request.POST.getlist('models_to_scan')
        context['selected_options'] = selected_options

        if selected_options:
            # Uruchamiamy serwis z wybranymi opcjami
            results = asset_audit_service.run_asset_audit(models_to_scan=selected_options)
            context['audit_results'] = results
            # Obliczamy łączną liczbę problemów
            context['total_problems_count'] = sum(len(problems) for problems in results.values())
        else:
            # Możemy dodać komunikat, jeśli nic nie zostało wybrane
            from django.contrib import messages
            messages.warning(request, "Nie wybrano żadnej kategorii do przeskanowania.")

    return render(request, 'odznaki/tools/asset_audit.html', context)