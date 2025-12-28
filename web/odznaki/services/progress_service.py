# odznaki/services/progress_service.py
import logging
from django.db.models import Count, Q, F, Func, Value, IntegerField

logger = logging.getLogger(__name__)

def annotate_badges_with_progress(badge_queryset):
    """
    Przyjmuje QuerySet odznak i dodaje do niego adnotacje z obliczonym postępem.
    Używa warunkowej agregacji do zliczania zaliczonych POI.
    """
    # Warunek czasowy: wizyta musi pasować do ram czasowych odznaki.
    # Używamy F() do odwoływania się do pól odznaki wewnątrz relacji.
    date_conditions = Q(
        Q(badge_requirements__point_of_interest__visits__visit_date__gte=F('start_date')) | Q(start_date__isnull=True),
        Q(badge_requirements__point_of_interest__visits__visit_date__lte=F('end_date')) | Q(end_date__isnull=True)
    )

    # Adnotacja, która zlicza unikalne POI, które mają wizytę spełniającą warunki
    annotated_queryset = badge_queryset.annotate(
        achieved_poi_count=Count(
            'badge_requirements__point_of_interest__visits__point_of_interest',
            filter=date_conditions,
            distinct=True
        )
    ).annotate(
        # Oblicz procent, zabezpieczając się przed dzieleniem przez zero
        percentage=Func(
            100.0 * F('achieved_poi_count') / F('required_poi_count'),
            function='NULLIF',
            template='%(function)s(%(expressions)s, 0)',
            output_field=IntegerField()
        )
    )

    return annotated_queryset