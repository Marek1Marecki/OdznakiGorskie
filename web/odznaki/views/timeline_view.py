# odznaki/views/timeline_view.py

from django.shortcuts import render
from odznaki.models import Visit, BadgeLevel, Trip


def timeline_view(request):
    """
    Widok generujący chronologiczną oś czasu ze wszystkich aktywności.
    """
    all_events = []

    # 1. Pobierz wszystkie wizyty
    visits = Visit.objects.select_related('point_of_interest').order_by('-visit_date')

    # Przygotujmy słownik wycieczek dla szybkiego dostępu
    trips_by_date = {trip.date: trip for trip in Trip.objects.all()}

    for visit in visits:
        all_events.append({
            'event_type': 'visit',
            'event_date': visit.visit_date,
            'title': visit.point_of_interest.name,
            'related_trip': trips_by_date.get(visit.visit_date),
            'object': visit
        })

    # 2. Pobierz wszystkie zdobyte (otrzymane) stopnie odznak
    achieved_levels = BadgeLevel.objects.select_related('badge').filter(
        received_at__isnull=False
    ).order_by('-received_at')

    for level in achieved_levels:
        all_events.append({
            'event_type': 'badge_level',
            'event_date': level.received_at,
            'title': f"{level.badge.name} - {level.get_level_display()}",
            'object': level
        })

    # 3. Posortuj wszystkie wydarzenia chronologicznie
    sorted_events = sorted(all_events, key=lambda x: x['event_date'], reverse=True)

    context = {
        'events': sorted_events
    }

    return render(request, 'odznaki/timeline.html', context)
