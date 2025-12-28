# odznaki/views/dashboard_views.py
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
from datetime import date, timedelta
from django.db.models import Q

# Importujemy wszystkie potrzebne modele i serwisy
from odznaki.models import BadgeNewsItem, BadgeLevel, Badge, PointOfInterest, Visit
from odznaki.services import scoring_service


# =======================================================================
# --- PODFUNKCJE WEWNĘTRZNE DLA DASHBOARDU ---
# Każda funkcja ma jedną odpowiedzialność
# =======================================================================

def _get_logistics_data():
    """
    Pobiera i przetwarza dane dla tablicy Kanban.
    Wersja 2.0: Poprawnie obsługuje odznaki wielostopniowe.
    """
    today = date.today()
    logistics_data = {'to_send': [], 'in_verification': [], 'to_be_delivered': [], 'to_collect': []}

    # 1. Pobieramy WSZYSTKIE stopnie, które nie są jeszcze wpięte do albumu.
    #    Dodajemy adnotację z liczbą zdobytych POI dla nadrzędnej odznaki.
    #    Używamy `progress_service` do reużycia sprawdzonej logiki.
    from odznaki.services import progress_service

    levels_qs = BadgeLevel.objects.filter(collected_at__isnull=True).select_related('badge')
    badge_ids = [level.badge.id for level in levels_qs]

    # Adnotujemy odznaki, aby uzyskać `achieved_poi_count`
    badges_with_progress = progress_service.annotate_badges_with_progress(
        Badge.objects.filter(id__in=badge_ids)
    )
    # Tworzymy mapę dla szybkiego dostępu
    achieved_counts_map = {badge.id: badge.achieved_poi_count for badge in badges_with_progress}

    # 2. Iterujemy i filtrujemy w Pythonie
    verification_threshold = today - timedelta(days=30)
    delivery_threshold = today - timedelta(days=14)

    for level in levels_qs:
        badge_achieved_count = achieved_counts_map.get(level.badge.id, 0)

        # --- NOWY, KLUCZOWY WARUNEK ---
        # Stopień jest "gotowy do wysyłki", jeśli liczba zdobytych POI
        # jest wystarczająca dla TEGO stopnia.
        is_ready_for_logistics = badge_achieved_count >= level.poi_count

        # Jeśli ustawiono już datę wysłania, zakładamy, że był gotowy
        was_sent = level.sent_at is not None

        if is_ready_for_logistics or was_sent:
            level.is_overdue = False
            if level.sent_at is None:
                logistics_data['to_send'].append(level)
            elif level.verified_at is None:
                if level.sent_at < verification_threshold: level.is_overdue = True
                logistics_data['in_verification'].append(level)
            elif level.received_at is None:
                if level.verified_at < delivery_threshold: level.is_overdue = True
                logistics_data['to_be_delivered'].append(level)
            elif level.collected_at is None:
                logistics_data['to_collect'].append(level)

    return logistics_data


def _get_expiring_badges_data():
    """Pobiera dane o odznakach, których termin wkrótce upływa."""
    today = date.today()
    three_months_from_now = today + timedelta(days=90)

    expiring_badges = Badge.objects.filter(
        is_fully_achieved=False, end_date__isnull=False,
        end_date__gte=today, end_date__lte=three_months_from_now
    ).order_by('end_date')

    for badge in expiring_badges:
        badge.days_left = (badge.end_date - today).days

    return expiring_badges


def _get_dashboard_scoring_data():
    """
    Pobiera dane scoring'owe dla dashboardu.
    """
    scoring_data = scoring_service.calculate_all_dashboard_scores()
    return scoring_data


def _get_general_stats_data():
    """
    Pobiera ogólne statystyki.
    """
    
    today = date.today()
    all_badges = Badge.objects.all()
    achieved_badges_count = all_badges.filter(is_fully_achieved=True).count()
    in_progress_badges_count = all_badges.filter(
        is_fully_achieved=False,
    ).filter(
        Q(end_date__gte=today) | Q(end_date__isnull=True)
    ).count()
    visited_pois_count = Visit.objects.values('point_of_interest').distinct().count()
    total_pois_count = PointOfInterest.objects.count()

    general_stats = {
        'total_badges': all_badges.count(),
        'achieved_badges': achieved_badges_count,
        'in_progress_badges': in_progress_badges_count,
        'visited_pois': visited_pois_count,
        'total_pois': total_pois_count,
    }
    return general_stats


# =======================================================================
# --- GŁÓWNY WIDOK DASHBOARDU ---
# Teraz korzysta ze zoptymalizowanych funkcji scoring'owych
# =======================================================================


def dashboard_view(request):
    """
    Główny, zrefaktoryzowany widok strony startowej (dashboardu),
    który używa zoptymalizowanych funkcji scoring'owych eliminujących duplikaty zapytań.
    """
    # Pobierz dane scoring'owe (top POI i regiony) w jednym przejściu
    scoring_data = _get_dashboard_scoring_data()

    context = {
        'logistics_data': _get_logistics_data(),
        'news_items': BadgeNewsItem.objects.filter(is_dismissed=False),
        'expiring_badges': _get_expiring_badges_data(),

        'top_pois': scoring_data['top_pois'],
        'top_regions': scoring_data['top_regions'],
        'general_stats': _get_general_stats_data(),
    }

    return render(request, 'odznaki/dashboard.html', context)


# Widok `dismiss_multiple_news_items_view` pozostaje bez zmian
@require_POST
def dismiss_multiple_news_items_view(request):
    """
    Widok do masowego oznaczania wielu wiadomości jako ukrytych.
    """
    item_ids_to_dismiss = request.POST.getlist('item_ids')
    if item_ids_to_dismiss:
        updated_count = BadgeNewsItem.objects.filter(id__in=item_ids_to_dismiss).update(is_dismissed=True)
        if updated_count > 0:
            messages.success(request, f"Pomyślnie ukryto {updated_count} wpisów.")
        else:
            messages.warning(request, "Nie znaleziono żadnych wpisów do ukrycia.")
    else:
        messages.info(request, "Nie zaznaczono żadnych wpisów do ukrycia.")
    return redirect(reverse('odznaki:dashboard'))
