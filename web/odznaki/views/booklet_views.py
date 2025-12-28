# odznaki/views/booklet_views.py

from django.shortcuts import render, get_object_or_404
from django.db.models import Prefetch, Subquery, OuterRef
from datetime import date

from odznaki.models import Booklet, Visit, BookletType, Badge, Organizer
from odznaki.services import badge_service
from odznaki.services import progress_service

import logging

logger = logging.getLogger(__name__)  # Dodaj logger na poziomie modułu


def booklet_list_view(request):
    """
    Widok wyświetlający listy książeczek, pogrupowane na GOT i pozostałe.
    Wersja 2.0: Użycie prefetch_related dla niezawodnego pobierania organizatorów.
    """
    logger.info("\n--- DEBUG: Uruchomiono widok booklet_list_view ---")

    # --- POPRAWKA JEST TUTAJ ---
    # Zamiast `select_related`, używamy `prefetch_related`.
    all_booklets = Booklet.objects.prefetch_related('organizer').order_by('name')
    # --- KONIEC POPRAWKI ---

    # Celowo dodajemy .count() tutaj, aby wymusić wykonanie zapytania i zobaczyć logi.
    logger.info(f"Pobrano {all_booklets.count()} wszystkich książeczek z bazy.")

    got_booklets = []
    other_booklets = []

    for b in all_booklets:
        # Ta część logiki pozostaje bez zmian.
        org_name = b.organizer.name if b.organizer else "Brak"
        logger.info(f"  -> Przetwarzam: '{b.name}' (Typ: {b.booklet_type}, Organizator: {org_name})")
        if b.booklet_type == BookletType.GENERAL_GOT:
            got_booklets.append(b)
        else:
            other_booklets.append(b)

    logger.info(f"Podział: {len(got_booklets)} książeczek GOT, {len(other_booklets)} pozostałych.")

    context = {
        'got_booklets': got_booklets,
        'other_booklets': other_booklets,
    }

    logger.info("--- DEBUG: Koniec widoku, renderuję szablon ---\n")
    return render(request, 'odznaki/booklet_list.html', context)


def booklet_detail_view(request, pk):
    """
    Widok wyświetlający szczegółowy profil jednej książeczki,
    z postępem obliczanym dla każdej powiązanej odznaki osobno.
    """
    booklet = get_object_or_404(
        Booklet.objects.prefetch_related(
            'associated_badges__levels',
            'associated_badges__points_of_interest'
        ),
        pk=pk
    )

    # Pobieramy wszystkie wizyty raz, aby uniknąć zapytań w pętli
    all_visits = Visit.objects.all()
    badges_with_progress = []

    # --- UŻYWAMY SPRAWDZONEJ, NIEZAWODNEJ LOGIKI W PĘTLI ---
    for badge in booklet.associated_badges.all():

        poi_ids_in_badge = {poi.id for poi in badge.points_of_interest.all()}
        relevant_visits = all_visits.filter(point_of_interest_id__in=poi_ids_in_badge)

        visited_poi_ids_for_badge = set()
        for visit in relevant_visits:
            if (not badge.start_date or visit.visit_date >= badge.start_date) and \
                (not badge.end_date or visit.visit_date <= badge.end_date):
                visited_poi_ids_for_badge.add(visit.point_of_interest_id)

        achieved_count = len(visited_poi_ids_for_badge)
        required_count = badge.required_poi_count
        percentage = (achieved_count / required_count) * 100 if required_count > 0 else 0

        levels_with_progress = []
        for level in badge.levels.all():
            lvl_required = level.poi_count
            lvl_achieved = min(achieved_count, lvl_required)
            lvl_percentage = (lvl_achieved / lvl_required) * 100 if lvl_required > 0 else 0
            levels_with_progress.append({
                'level': level, 'achieved_count': lvl_achieved,
                'required_count': lvl_required, 'percentage': round(lvl_percentage),
            })

        badges_with_progress.append({
            'badge': badge, 'achieved_count': achieved_count,
            'required_count': required_count, 'percentage': round(percentage),
            'levels_with_progress': levels_with_progress
        })
    # --- KONIEC SPRAWDZONEJ LOGIKI ---

    context = {
        'booklet': booklet,
        'badges_with_progress': badges_with_progress,
        'today': date.today()
    }

    return render(request, 'odznaki/booklet_detail.html', context)
