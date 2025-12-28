# odznaki/views/poi_history_view.py
from django.shortcuts import render, get_object_or_404
from odznaki.models import PointOfInterest, Trip


def poi_history_view(request, poi_id):
    """
    Widok wyświetlający historię wizyt i zdjęć dla jednego POI.
    """
    poi = get_object_or_404(
        PointOfInterest.objects.prefetch_related('visits', 'photos'),
        id=poi_id
    )

    # 1. Grupujemy zdjęcia według daty ich wykonania
    photos_by_date = {}
    for photo in poi.photos.all():
        if photo.photo_date:
            if photo.photo_date not in photos_by_date:
                photos_by_date[photo.photo_date] = []
            photos_by_date[photo.photo_date].append(photo)

    # 2. Przygotowujemy listę wizyt, "doklejając" do każdej pasujące zdjęcia
    visits_with_context = []
    for visit in poi.visits.all().order_by('-visit_date'):
        # Szukamy powiązanej wycieczki
        trip_for_visit = Trip.objects.filter(date=visit.visit_date).first()

        visits_with_context.append({
            'visit': visit,
            'trip': trip_for_visit,
            'photos': photos_by_date.get(visit.visit_date, [])  # Pobierz zdjęcia z tej samej daty
        })

    context = {
        'poi': poi,
        'visits_with_context': visits_with_context,
    }

    return render(request, 'odznaki/poi_history.html', context)
