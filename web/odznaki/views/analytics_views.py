# odznaki/views/analytics_views.py

from django.shortcuts import render
# Poprawnie importujemy nasz serwis
from odznaki.services import analytics_service
from odznaki.utils.map_utils import create_gpx_heatmap_with_folium


def mesoregion_activity_view(request):
    """
    Widok dla rankingu aktywności w mezoregionach.
    """
    # Wywołujemy funkcję z serwisu, która robi całą ciężką pracę
    activity_data = analytics_service.calculate_activity_by_mesoregion()

    context = {
        'activity_ranking': activity_data
    }
    return render(request, 'odznaki/analytics/mesoregion_activity.html', context)


# --- NOWY WIDOK DLA STATYSTYK ROCZNYCH ---
def yearly_stats_view(request):
    """
    Widok dla strony ze statystykami rocznymi i interaktywnym wykresem.
    """
    # 1. Pobierz zagregowane dane z serwisu
    yearly_stats = analytics_service.get_yearly_stats()

    # 2. Przygotuj dane specjalnie dla wykresu Chart.js
    #    Chcemy mieć osobne listy dla etykiet (lat) i dla każdej metryki.
    chart_data = {
        'labels': [], 'distance': [], 'elevation': [], 'got_points': [],
        'new_pois': [], 'badges': [], 'trips': [], 'everest': [], 'regions': [] # <-- Dodaj brakujące klucze
    }
    # Iterujemy po posortowanych danych (od najstarszego do najnowszego dla wykresu)
    for stats in sorted(yearly_stats, key=lambda x: x['year']):
        chart_data['labels'].append(stats['year'])
        chart_data['distance'].append(stats['total_distance_km'])
        chart_data['elevation'].append(stats['total_elevation_gain_m'])
        chart_data['got_points'].append(stats['total_got_points'])
        chart_data['new_pois'].append(stats['new_pois_count'])
        chart_data['badges'].append(stats['badges_earned_count'])
        # --- NOWE LINIE ---
        chart_data['trips'].append(stats['trip_count'])
        chart_data['everest'].append(stats['total_everest_m'])
        chart_data['regions'].append(stats['visited_mesoregions_count'])

    context = {
        'yearly_stats': yearly_stats,  # Dane dla tabeli (posortowane od najnowszego)
        'chart_data': chart_data,  # Dane dla wykresu (posortowane od najstarszego)
    }

    return render(request, 'odznaki/analytics/yearly_stats.html', context)


# --- NOWY WIDOK DLA MAPY ŚLADÓW GPX ---
def gpx_heatmap_view(request):
    """
    Widok generujący mapę cieplną ze wszystkich śladów GPX,
    korzystając z dedykowanego kreatora.
    """
    # 1. Pobierz dane (bez zmian)
    heatmap_data = analytics_service.get_gpx_heatmap_data(segment_length_m=50)

    # 2. Wywołaj funkcję z API map, która zrobi całą resztę
    folium_map_html = create_gpx_heatmap_with_folium(request, heatmap_data)

    context = {
        'folium_map': folium_map_html,
    }
    return render(request, 'odznaki/analytics/gpx_heatmap.html', context)


def profile_stats_view(request):
    """
    Widok generujący stronę "Profilu Zdobywcy" z osobistymi rekordami
    i zagregowanymi statystykami.
    """
    personal_records = analytics_service.get_personal_records()

    context = {'records': personal_records,}

    return render(request, 'odznaki/analytics/profile_stats.html', context)
