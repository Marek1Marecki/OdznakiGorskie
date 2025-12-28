# odznaki/views/organizer_views.py

from django.shortcuts import render, get_object_or_404
from django.db.models import Count, OuterRef, Subquery, Q, Case, When, Value, IntegerField

from datetime import date

from odznaki.models import Organizer, PointOfInterest, Badge, Booklet, Visit, MesoRegion, BadgeRequirement
from odznaki.services import progress_service
from odznaki.utils.map_utils import create_organizer_map_with_folium

import logging # <-- DODAJEMY IMPORT
logger = logging.getLogger(__name__)


def organizer_list_view(request):
    """
    Widok wyświetlający listę wszystkich organizatorów z podstawowymi statystykami.
    """
    badge_count_subquery = Badge.objects.filter(organizer_id=OuterRef('pk')).values('organizer_id').annotate(
        count=Count('pk')).values('count')
    organizers = Organizer.objects.annotate(badge_count=Subquery(badge_count_subquery)).order_by('name')
    context = {'organizers_list': organizers}
    return render(request, 'odznaki/organizer_list.html', context)


def organizer_detail_view(request, pk):
    """
    Wersja 2.4: Ostateczna, w pełni poprawna i czytelna wersja
    z filtrowaniem, sortowaniem i pigułkami.
    """
    # === SEKCJA 1: POBIERANIE DANYCH PODSTAWOWYCH ===
    organizer = get_object_or_404(Organizer, pk=pk)
    today = date.today()

    # --- Pobierz opcje dla filtrów (tylko relevantne mezoregiony)
    badge_ids_for_organizer = organizer.badges.values_list('id', flat=True)
    mesoregion_ids = BadgeRequirement.objects.filter(
        badge_id__in=badge_ids_for_organizer,
        point_of_interest__mesoregion__isnull=False
    ).values_list('point_of_interest__mesoregion_id', flat=True).distinct()
    all_mesoregions_for_filter = MesoRegion.objects.filter(id__in=mesoregion_ids).order_by('name')

    # --- Pobierz i zwaliduj parametry GET
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'name_asc')

    mesoregion_param = request.GET.get('mesoregion', 'all')
    mesoregion_id = int(mesoregion_param) if mesoregion_param.isdigit() else None

    # === SEKCJA 2: FILTROWANIE I SORTOWANIE ODZNAK ===
    base_badges_qs = organizer.badges.prefetch_related('levels').all()

    # --- Filtrowanie na poziomie bazy danych
    if search_query:
        base_badges_qs = base_badges_qs.filter(name__icontains=search_query)
    if mesoregion_id:
        base_badges_qs = base_badges_qs.filter(points_of_interest__mesoregion__id=mesoregion_id).distinct()

    # --- Obliczanie postępu
    badges_with_progress_qs = progress_service.annotate_badges_with_progress(base_badges_qs)

    # --- Filtrowanie po obliczonym postępie
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

    # --- Sortowanie
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

    # --- Przygotowanie danych dla szablonu
    final_badges_list = []
    for badge in sorted_badges:
        levels_with_progress = []
        for level in badge.levels.all():
            lvl_required = level.poi_count
            lvl_achieved = min(badge.achieved_poi_count, lvl_required)
            lvl_percentage = (lvl_achieved / lvl_required) * 100 if lvl_required > 0 else 0
            levels_with_progress.append({'level': level, 'achieved_count': lvl_achieved, 'required_count': lvl_required,
                                         'percentage': round(lvl_percentage)})
        final_badges_list.append(
            {'badge': badge, 'achieved_count': badge.achieved_poi_count, 'required_count': badge.required_poi_count,
             'percentage': round(badge.percentage or 0), 'levels_with_progress': levels_with_progress})

    # === SEKCJA 3: PRZYGOTOWANIE DANYCH DLA PIGUŁEK ===
    active_filters = []
    if search_query:
        active_filters.append({'type': 'search', 'label': 'Fraza', 'value': search_query})
    if status_filter != 'all':
        status_labels = {'not_started': 'Nierozpoczęte', 'in_progress': 'W trakcie', 'achieved': 'Zdobyte',
                         'archival': 'Archiwalne'}
        active_filters.append({'type': 'status', 'label': 'Status', 'value': status_labels.get(status_filter)})
    if mesoregion_id:
        try:
            region_name = MesoRegion.objects.get(pk=mesoregion_id).name
            active_filters.append({'type': 'mesoregion', 'label': 'Mezoregion', 'value': region_name})
        except ObjectDoesNotExist:
            pass

    # === SEKCJA 4: GENEROWANIE MAPY ===
    # Mapa jest oparta na przefiltrowanych odznakach (`badges_with_progress_qs`)
    all_poi_ids_for_map = PointOfInterest.objects.filter(
        badge_requirement__badge__in=badges_with_progress_qs
    ).values_list('id', flat=True).distinct()
    poi_queryset_for_map = PointOfInterest.objects.filter(id__in=all_poi_ids_for_map)
    folium_map = create_organizer_map_with_folium(
        poi_queryset=poi_queryset_for_map,
        badges_context_qs=badges_with_progress_qs,
        request=request
    )

    # === SEKCJA 5: BUDOWANIE FINALNEGO KONTEKSTU ===
    context = {
        'organizer': organizer,
        'badges_with_progress': final_badges_list,
        'folium_map': folium_map,
        'today': today,
        'hide_organizer_column': True,
        'all_mesoregions': all_mesoregions_for_filter,
        'current_filters': {
            'status': status_filter,
            'mesoregion': mesoregion_id or 'all',
            'search': search_query,
            'sort': sort_by,
        },
        'active_filters': active_filters,
        'total_badge_count': organizer.badges.count(),
    }

    return render(request, 'odznaki/organizer_detail.html', context)
