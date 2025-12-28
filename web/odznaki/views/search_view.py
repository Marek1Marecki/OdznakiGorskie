# odznaki/views/search_view.py

from django.shortcuts import render
from django.db.models import Q
from odznaki.models import Badge, PointOfInterest, MesoRegion, Trip, Organizer


def search_view(request):
    """
    Widok obsługujący globalne wyszukiwanie w całej aplikacji.
    """
    # Pobieramy frazę wyszukiwania z parametrów GET ?q=...
    query = request.GET.get('q', '')

    results = {
        'badges': Badge.objects.none(),
        'pois': PointOfInterest.objects.none(),
        'regions': MesoRegion.objects.none(),
        'trips': Trip.objects.none(),
        'organizers': Organizer.objects.none(),
    }

    # Upewniamy się, że wyszukujemy tylko, jeśli fraza nie jest pusta
    if query:
        # --- Wyszukiwanie Odznak ---
        results['badges'] = Badge.objects.filter(
            name__icontains=query
        )

        # --- Wyszukiwanie Punktów POI ---
        results['pois'] = PointOfInterest.objects.filter(
            Q(name__icontains=query) | Q(secondary_name__icontains=query)
        ).select_related('mesoregion')

        # --- Wyszukiwanie Mezoregionów ---
        results['regions'] = MesoRegion.objects.filter(
            name__icontains=query
        )

        # --- Wyszukiwanie Wycieczek ---
        results['trips'] = Trip.objects.filter(
            Q(start_point_name__icontains=query) | Q(end_point_name__icontains=query) | Q(description__icontains=query)
        )

        # --- Wyszukiwanie Organizatorów ---
        results['organizers'] = Organizer.objects.filter(
            name__icontains=query
        )

    context = {
        'query': query,
        'results': results,
        # Zliczamy, czy w ogóle znaleziono jakiekolwiek wyniki
        'found_results': any(qs.exists() for qs in results.values())
    }

    return render(request, 'odznaki/search_results.html', context)

