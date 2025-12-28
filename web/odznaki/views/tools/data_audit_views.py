# odznaki/views/tools/data_audit_views.py

from django.shortcuts import render
from odznaki.models import PointOfInterest


def missing_coordinates_audit_view(request):
    """
    Widok dla narzędzia wyszukującego punkty POI bez zdefiniowanych współrzędnych.
    """
    # Wykonujemy jedno, proste zapytanie do bazy danych
    pois_without_location = PointOfInterest.objects.filter(
        location__isnull=True
    ).order_by('name')

    context = {
        'problematic_pois': pois_without_location,
    }

    return render(request, 'odznaki/tools/missing_coordinates_audit.html', context)
