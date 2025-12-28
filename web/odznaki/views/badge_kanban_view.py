# odznaki/views/badge_kanban_view.py
from django.shortcuts import render
from odznaki.models import BadgeLevel, Visit
from collections import defaultdict


def badge_kanban_view(request):
    # Pobieramy wszystkie wizyty raz, aby zoptymalizować
    all_visits = Visit.objects.all()
    # Tworzymy mapę {poi_id: [daty wizyt]}
    visits_by_poi = defaultdict(list)
    for visit in all_visits:
        visits_by_poi[visit.point_of_interest_id].append(visit.visit_date)

    # Pobieramy wszystkie poziomy, od razu z odznakami i ich POI
    all_levels = BadgeLevel.objects.select_related('badge').prefetch_related('badge__points_of_interest').all()

    # Listy do kategoryzacji
    not_started = []
    in_progress = []
    achieved = []

    # Słownik do cache'owania obliczeń dla nadrzędnych odznak
    badge_progress_cache = {}

    for level in all_levels:
        badge = level.badge
        if badge.id not in badge_progress_cache:
            # Oblicz postęp dla nadrzędnej odznaki (jeśli jeszcze nie był liczony)
            poi_ids_in_badge = {poi.id for poi in badge.points_of_interest.all()}

            achieved_count = 0
            for poi_id in poi_ids_in_badge:
                if poi_id in visits_by_poi:
                    for visit_date in visits_by_poi[poi_id]:
                        if (not badge.start_date or visit_date >= badge.start_date) and \
                            (not badge.end_date or visit_date <= badge.end_date):
                            achieved_count += 1
                            break  # Wystarczy jedna pasująca wizyta
            badge_progress_cache[badge.id] = achieved_count

        # Oblicz postęp dla konkretnego stopnia
        badge_achieved_count = badge_progress_cache[badge.id]
        level_required = level.poi_count
        level_achieved = min(badge_achieved_count, level_required)
        percentage = (level_achieved / level_required) * 100 if level_required > 0 else 0

        level_data = {
            'level': level,
            'achieved_count': level_achieved,
            'required_count': level_required,
            'percentage': percentage,
        }

        # Kategoryzacja
        if percentage >= 100:
            achieved.append(level_data)
        elif percentage > 0:
            in_progress.append(level_data)
        else:
            not_started.append(level_data)

    # Sortowanie każdej kolumny
    not_started.sort(key=lambda x: x['percentage'], reverse=True)
    in_progress.sort(key=lambda x: x['percentage'], reverse=True)
    achieved.sort(key=lambda x: x['percentage'], reverse=True)

    context = {
        'not_started_levels': not_started,
        'in_progress_levels': in_progress,
        'achieved_levels': achieved,
    }
    return render(request, 'odznaki/badge_kanban.html', context)
