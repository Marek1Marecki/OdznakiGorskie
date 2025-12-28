# odznaki/enums.py
from django.db import models

# === STAŁE DEFINIUJĄCE DOSTĘPNE STYLE ===
# Klasy TextChoices przeniesione z modelu TripSegment

class Color(models.TextChoices):
    RED = 'red', 'Czerwony'
    BLUE = 'blue', 'Niebieski'
    GREEN = 'green', 'Zielony'
    YELLOW = 'yellow', 'Żółty'
    BLACK = 'black', 'Czarny'

class LineCap(models.TextChoices):
    ROUND = 'round', 'Okrągły'
    SQUARE = 'square', 'Kwadratowy'
    BUTT = 'butt', 'Płaski'

class LineJoin(models.TextChoices):
    ROUND = 'round', 'Okrągłe'
    BEVEL = 'bevel', 'Skośne'
    MITER = 'miter', 'Ostre'

class DashArray(models.TextChoices):
    SOLID = '', 'Linia ciągła'
    SHORT = '5,1', 'Krótka kreska'
    MEDIUM = '10,2', 'Średnia kreska'
    LONG = '15,3', 'Długa kreska'
    DOT = '2,2', 'Kropkowana'

class DashOffset(models.TextChoices):
    NONE = '0', 'Brak'
    SMALL = '2', 'Małe wcięcie'
    LARGE = '4', 'Duże wcięcie'

# === KONIEC STAŁYCH ===