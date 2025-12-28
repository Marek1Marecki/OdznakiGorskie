# odznaki/views/tools/potential_visits_view.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.http import require_POST

from odznaki.models import PointOfInterest, Trip, Visit
from odznaki.services.tools_service import find_potential_visits_from_gpx
from odznaki.services import visit_service

def potential_visits_finder_view(request):
    """
    Widok dla narzędzia "Odkrywca Potencjalnych Zaliczeń".
    """
    # Wywołujemy serwis, aby uzyskać listę sugestii
    suggestions = find_potential_visits_from_gpx()

    context = {
        'suggestions': suggestions,
    }

    return render(request, 'odznaki/tools/potential_visits.html', context)


@require_POST
def create_visit_from_suggestion_view(request):
    """
    Tworzy obiekt Visit na podstawie danych z formularza (sugestii).
    """
    try:
        poi_id = int(request.POST.get('poi_id'))
        trip_id = int(request.POST.get('trip_id'))

        poi = get_object_or_404(PointOfInterest, pk=poi_id)
        trip = get_object_or_404(Trip, pk=trip_id)

        # Sprawdzamy, czy wizyta już nie istnieje, aby uniknąć duplikatów
        # Sprawdzamy, czy wizyta już nie istnieje
        if Visit.objects.filter(point_of_interest=poi, visit_date=trip.date).exists():
            messages.info(request, f"Wpis Visit dla '{poi.name}' z datą {trip.date} już istniał.")
            created = False
        else:
            # Tworzymy nową instancję i używamy naszego serwisu do jej zapisu
            new_visit = Visit(
                point_of_interest=poi,
                visit_date=trip.date,
                description=f"Wizyta zaliczona na podstawie przejścia trasy '{trip}'."
            )
            visit_service.create_or_update_visit(new_visit)
            created = True

        if created:
            messages.success(request, f"Pomyślnie utworzono wpis Visit dla '{poi.name}' z datą {trip.date}.")
        else:
            messages.info(request, f"Wpis Visit dla '{poi.name}' z datą {trip.date} już istniał.")

    except (ValueError, TypeError) as e:
        messages.error(request, f"Wystąpił błąd danych: {e}. Nie udało się utworzyć wpisu.")

    # Przekierowujemy z powrotem na stronę narzędzia
    return redirect(reverse('odznaki:tool-potential-visits'))