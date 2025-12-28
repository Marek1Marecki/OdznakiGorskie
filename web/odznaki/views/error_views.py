# odznaki/views/error_views.py
from django.shortcuts import render


def handler404(request, exception):
    """
    Niestandardowy widok dla błędu 404 - Nie znaleziono strony.
    """
    return render(request, 'odznaki/errors/404.html', status=404)


def handler500(request):
    """
    Niestandardowy widok dla błędu 500 - Błąd serwera.
    """
    return render(request, 'odznaki/errors/500.html', status=500)