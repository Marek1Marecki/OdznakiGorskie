# odznaki/views/badge_list_views.py
from django.shortcuts import render
from django.db.models import Q, Case, When, Value, IntegerField, ObjectDoesNotExist
from django.http import HttpResponse
from datetime import date
import csv

from odznaki.models import Badge, Organizer, MesoRegion, BadgeRequirement
from odznaki.services import progress_service


def handle_badge_csv_export(request):
    """
    Generuje i zwraca plik CSV z przefiltrowaną listą odznak.
    """
    # KROK 1: Ponownie wykorzystaj logikę filtrowania z głównego widoku
    today = date.today()
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '').strip()
    organizer_param = request.GET.get('organizer', 'all')
    organizer_id = int(organizer_param) if organizer_param.isdigit() else None
    mesoregion_param = request.GET.get('mesoregion', 'all')
    mesoregion_id = int(mesoregion_param) if mesoregion_param.isdigit() else None

    badges_qs = Badge.objects.all()
    if search_query: badges_qs = badges_qs.filter(name__icontains=search_query)
    if organizer_id: badges_qs = badges_qs.filter(organizer__id=organizer_id)
    if mesoregion_id: badges_qs = badges_qs.filter(points_of_interest__mesoregion__id=mesoregion_id).distinct()

    badges_with_progress_qs = progress_service.annotate_badges_with_progress(badges_qs)

    if status_filter == 'not_started':
        badges_with_progress_qs = badges_with_progress_qs.filter(achieved_poi_count=0, is_fully_achieved=False).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True))
    elif status_filter == 'in_progress':
        badges_with_progress_qs = badges_with_progress_qs.filter(achieved_poi_count__gt=0,
                                                                 is_fully_achieved=False).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True))
    elif status_filter == 'achieved':
        badges_with_progress_qs = badges_with_progress_qs.filter(is_fully_achieved=True)
    elif status_filter == 'archival':
        badges_with_progress_qs = badges_with_progress_qs.filter(end_date__lt=today)

    results_qs = badges_with_progress_qs.select_related('organizer').order_by('name')

    # KROK 2: Przygotuj odpowiedź HTTP
    response = HttpResponse(content_type='text/csv', headers={
        'Content-Disposition': f'attachment; filename="badges_export_{date.today().isoformat()}.csv"'})
    response.write('\ufeff'.encode('utf8'))

    # KROK 3: Wygeneruj zawartość CSV
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Nazwa Odznaki', 'Organizator', 'Status', 'Postep (%)', 'Zdobyte POI', 'Wymagane POI'])

    for badge in results_qs:
        if badge.is_fully_achieved:
            status = 'Zdobyta'
        elif badge.end_date and badge.end_date < today:
            status = 'Archiwalna'
        elif badge.achieved_poi_count == 0:
            status = 'Nierozpoczęta'
        else:
            status = 'W trakcie'

        writer.writerow([
            badge.name,
            badge.organizer.name if badge.organizer else '',
            status,
            round(badge.percentage or 0),
            badge.achieved_poi_count,
            badge.required_poi_count
        ])

    return response


def list_badges(request):
    """
    Wersja 3.1: Z dodaną logiką dla pigułek aktywnych filtrów.
    """
    # --- Krok 1: Pobierz opcje dla filtrów ---
    all_organizers = Organizer.objects.filter(badge__isnull=False).distinct().order_by('name')
    mesoregion_ids = BadgeRequirement.objects.filter(point_of_interest__mesoregion__isnull=False).values_list(
        'point_of_interest__mesoregion_id', flat=True).distinct()
    all_mesoregions = MesoRegion.objects.filter(id__in=mesoregion_ids).order_by('name')
    today = date.today()

    # --- Krok 2: Pobierz i zwaliduj parametry z GET ---
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'name_asc')

    organizer_param = request.GET.get('organizer', 'all')
    organizer_id = int(organizer_param) if organizer_param.isdigit() else None

    mesoregion_param = request.GET.get('mesoregion', 'all')
    mesoregion_id = int(mesoregion_param) if mesoregion_param.isdigit() else None

    # --- Krok 3: Zbuduj QuerySet, aplikując filtry ---
    badges_qs = Badge.objects.prefetch_related(
        'levels'
    ).select_related('organizer').all()

    if search_query:
        badges_qs = badges_qs.filter(name__icontains=search_query)
    if organizer_id:
        badges_qs = badges_qs.filter(organizer__id=organizer_id)
    if mesoregion_id:
        badges_qs = badges_qs.filter(points_of_interest__mesoregion__id=mesoregion_id).distinct()

    # --- Krok 4: Oblicz postęp ---
    badges_with_progress_qs = progress_service.annotate_badges_with_progress(badges_qs)

    # --- Krok 5: Aplikuj filtry zależne od postępu ---
    if status_filter == 'not_started':
        badges_with_progress_qs = badges_with_progress_qs.filter(achieved_poi_count=0, is_fully_achieved=False).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True))
    elif status_filter == 'in_progress':
        badges_with_progress_qs = badges_with_progress_qs.filter(achieved_poi_count__gt=0,
                                                                 is_fully_achieved=False).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True))
    elif status_filter == 'achieved':
        badges_with_progress_qs = badges_with_progress_qs.filter(is_fully_achieved=True)
    elif status_filter == 'archival':
        badges_with_progress_qs = badges_with_progress_qs.filter(end_date__lt=today)

    # --- Krok 6: Zastosuj sortowanie ---
    if sort_by == 'progress_desc':
        order_expression = Case(When(percentage__gt=0, then=Value(0)), default=Value(1), output_field=IntegerField())
        sorted_badges = badges_with_progress_qs.annotate(has_progress=order_expression).order_by('has_progress',
                                                                                                 '-percentage')
    elif sort_by == 'progress_asc':
        order_expression = Case(When(percentage=0, then=Value(1)), default=Value(0), output_field=IntegerField())
        sorted_badges = badges_with_progress_qs.annotate(has_progress=order_expression).order_by('has_progress',
                                                                                                 'percentage')
    else:
        order_field = 'name' if sort_by == 'name_asc' else '-name'
        sorted_badges = badges_with_progress_qs.order_by(order_field)

    # --- Krok 7: Przygotuj dane dla szablonu ---
    final_badges_list = []
    for badge in sorted_badges:
        levels_with_progress = []
        for level in badge.levels.all():
            lvl_required = level.poi_count
            lvl_achieved = min(badge.achieved_poi_count, lvl_required)
            lvl_percentage = (lvl_achieved / lvl_required) * 100 if lvl_required > 0 else 0
            levels_with_progress.append({'level': level, 'achieved_count': lvl_achieved, 'required_count': lvl_required,
                                         'percentage': round(lvl_percentage), })
        final_badges_list.append(
            {'badge': badge, 'achieved_count': badge.achieved_poi_count, 'required_count': badge.required_poi_count,
             'percentage': round(badge.percentage or 0), 'levels_with_progress': levels_with_progress})

    # --- Krok 8: Budowanie listy aktywnych filtrów (pigułek) ---
    active_filters = []
    if search_query:
        active_filters.append({'type': 'search', 'label': 'Fraza', 'value': search_query})
    if status_filter != 'all':
        status_labels = {'not_started': 'Nierozpoczęte', 'in_progress': 'W trakcie', 'achieved': 'Zdobyte',
                         'archival': 'Archiwalne'}
        active_filters.append({'type': 'status', 'label': 'Status', 'value': status_labels.get(status_filter)})
    if organizer_id:
        try:
            org_name = Organizer.objects.get(pk=organizer_id).name
            active_filters.append({'type': 'organizer', 'label': 'Organizator', 'value': org_name})
        except ObjectDoesNotExist:
            pass
    if mesoregion_id:
        try:
            region_name = MesoRegion.objects.get(pk=mesoregion_id).name
            active_filters.append({'type': 'mesoregion', 'label': 'Mezoregion', 'value': region_name})
        except ObjectDoesNotExist:
            pass

    context = {
        'badges_list': final_badges_list,
        'all_organizers': all_organizers,
        'all_mesoregions': all_mesoregions,
        'current_filters': {
            'status': status_filter,
            'organizer': organizer_id or 'all',
            'mesoregion': mesoregion_id or 'all',
            'search': search_query,
            'sort': sort_by,
        },
        'active_filters': active_filters,
        'today': today
    }

    return render(request, 'odznaki/badge_list.html', context)
