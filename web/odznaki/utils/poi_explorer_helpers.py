# odznaki/utils/poi_explorer_helpers.py

from django.db.models import Q, Subquery, OuterRef, Count, Case, When, Value, F
from django.db.models.functions import Coalesce
from django.db import models
from datetime import date

from odznaki.models import Visit, PointOfInterest, Trip, Country, Province, SubProvince, MacroRegion, MesoRegion


def apply_db_filters(request, queryset):
    """Stosuje filtry, które są wydajne na poziomie bazy danych."""
    name_filter = request.GET.get('name', '')
    category_filter = request.GET.get('category', '')
    height_from_filter = request.GET.get('height_from', '')
    height_to_filter = request.GET.get('height_to', '')
    region_filter = request.GET.get('region', '')

    if name_filter: queryset = queryset.filter(name__icontains=name_filter)
    if category_filter: queryset = queryset.filter(category=category_filter)
    if height_from_filter.isdigit(): queryset = queryset.filter(height__gte=int(height_from_filter))
    if height_to_filter.isdigit(): queryset = queryset.filter(height__lte=int(height_to_filter))
    if region_filter and ':' in region_filter:
        region_type, region_id = region_filter.split(':', 1)
        if region_id.isdigit():
            queryset = queryset.filter(**{f'{region_type}_id': int(region_id)})

    return queryset


def apply_annotations(queryset):
    """Dodaje do QuerySetu złożone adnotacje (status, data ost. wizyty)."""
    today = date.today()
    last_visit_subquery = Visit.objects.filter(point_of_interest=OuterRef('pk')).order_by('-visit_date').values(
        'visit_date')[:1]

    active_badge_condition = Q(
        badge_requirement__badge__is_fully_achieved=False
    ) & (
                                 Q(badge_requirement__badge__start_date__lte=today) | Q(
                                 badge_requirement__badge__start_date__isnull=True)
                             ) & (
                                 Q(badge_requirement__badge__end_date__gte=today) | Q(
                                 badge_requirement__badge__end_date__isnull=True)
                             )

    claimed_condition = active_badge_condition & (
        (Q(visits__visit_date__gte=F('badge_requirement__badge__start_date')) | Q(
            badge_requirement__badge__start_date__isnull=True)) &
        (Q(visits__visit_date__lte=F('badge_requirement__badge__end_date')) | Q(
            badge_requirement__badge__end_date__isnull=True))
    )

    queryset = queryset.annotate(
        last_visit_date=Subquery(last_visit_subquery),
        visit_count=Coalesce(Count('visits', distinct=True), 0),
        claimed_count=Coalesce(Count('badge_requirement', filter=claimed_condition, distinct=True), 0),
        active_badge_count=Coalesce(Count('badge_requirement', filter=active_badge_condition, distinct=True), 0)
    ).annotate(
        status=Case(
            When(claimed_count__gt=0, then=Value('zdobyty')),
            When(visit_count__gt=0, then=Value('do_ponowienia')),
            When(active_badge_count__gt=0, then=Value('niezdobyty')),
            default=Value('nieaktywny'),
            output_field=models.CharField()
        )
    )
    return queryset


def apply_ordering(request, queryset):
    """Stosuje dynamiczne sortowanie na poziomie bazy danych."""
    order_column_index = int(request.GET.get('order[0][column]', 0))
    order_direction = request.GET.get('order[0][dir]', 'asc')

    column_mapping = ['name', 'status', 'height', 'category', 'mesoregion__name', 'voivodeship__name',
                      'last_visit_date']

    if order_column_index < len(column_mapping):
        order_by_field = column_mapping[order_column_index]
        if order_direction == 'desc':
            order_by_field = f'-{order_by_field}'
        return queryset.order_by(order_by_field)
    return queryset.order_by('name')


def prepare_json_data(paginated_queryset, poi_statuses, last_visits):
    """Przygotowuje ostateczną strukturę JSON dla DataTables."""
    visit_dates = [d for d in last_visits.values() if d]
    trips_by_date = {trip.date: trip.id for trip in Trip.objects.filter(date__in=visit_dates)} if visit_dates else {}

    data = []
    for poi in paginated_queryset:
        last_visit = last_visits.get(poi.id)
        data.append({
            'id': poi.id, 'name': poi.name, 'status': poi_statuses.get(poi.id, 'nieaktywny'), 'height': poi.height,
            'category': poi.get_category_display(),
            'mesoregion_name': poi.mesoregion.name if poi.mesoregion else '',
            'mesoregion_id': poi.mesoregion.id if poi.mesoregion else None,
            'voivodeship_name': poi.voivodeship.name if poi.voivodeship else '',
            'voivodeship_id': poi.voivodeship.id if poi.voivodeship else None,
            'last_visit_date': last_visit.strftime('%Y-%m-%d') if last_visit else '',
            'last_visit_trip_id': trips_by_date.get(last_visit),
        })
    return data
