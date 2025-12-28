from django.db import models
from django.contrib.gis.db import models as gis_models
from tinymce.models import HTMLField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .base import AbstractTimeStampedModel
from odznaki.enums import Color, DashArray, LineCap, LineJoin, DashOffset

from django.utils.safestring import mark_safe


class Trip(AbstractTimeStampedModel):
    """Reprezentuje pojedynczą wycieczkę, która może składać się z odcinków GPX.

    Atrybuty:
        start_point_name (CharField): Nazwa punktu początkowego wycieczki.
        end_point_name (CharField): Nazwa punktu końcowego wycieczki.
        description (TextField): Opis wycieczki, trasy i atrakcji.
        date (DateField): Data odbycia wycieczki.

    Uwagi:
        Klasa przechowuje podstawowe informacje o wycieczce i zarządza
        powiązanymi z nią odcinkami GPX.
    """

    start_point_name = models.CharField(
        max_length=100,
        verbose_name="Nazwa punktu początkowego",
        help_text="Nazwa punktu początkowego wycieczki.",
    )
    end_point_name = models.CharField(
        max_length=100,
        verbose_name="Nazwa punktu końcowego",
        help_text="Nazwa punktu końcowego wycieczki.",
    )
    description = HTMLField(
        blank=True,
        verbose_name="Opis",
        help_text="Szczegółowy opis wycieczki, trasy i atrakcji."
    )
    date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data odbycia",
        help_text="Data odbycia wycieczki.",
        db_index=True  # Dodany indeks dla sortowania i filtrowania po dacie
    )
    total_distance_km = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        verbose_name="Całkowity dystans (km)",
        editable=False
    )
    total_elevation_gain_m = models.PositiveIntegerField(
        default=0,
        verbose_name="Suma podejść (m)",
        editable=False
    )
    got_points = models.PositiveIntegerField(
        default=0,
        verbose_name="Punkty GOT",
        editable=False
    )
    everest_diff_m = models.PositiveIntegerField(
        default=0,
        verbose_name='"Everest" (m)',
        editable=False
    )

    class Meta:
        db_table = 'odznaki_trip'
        verbose_name = 'Wycieczka'
        verbose_name_plural = 'Wycieczki'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['got_points']),
        ]

    def __str__(self):
        # Zwracamy teraz tylko nazwę trasy, bez daty.
        return f"{self.start_point_name} → {self.end_point_name}"

    @property
    def total_gpx_paths(self):
        """Zwraca liczbę odcinków GPX w wycieczce."""
        return self.gpx_paths.count()


class TripSegment(AbstractTimeStampedModel):
    """Model reprezentujący pojedynczy odcinek trasy w wycieczce.

    Atrybuty:
        start_point_name (CharField): Nazwa punktu początkowego
        end_point_name (CharField): Nazwa punktu końcowego
        gpx_path (LineStringField): Geometria ścieżki GPX
        order (PositiveSmallIntegerField): Kolejność odcinka w wycieczce

    Uwagi:
        Parametry stylizacji linii na mapie (kolor, grubość, styl) zostały przeniesione
        do modułu serwisowego odznaki.services.trip_service.
    """

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='gpx_paths',
        verbose_name="Wycieczka",
    )
    start_point_name = models.CharField(
        max_length=100,
        verbose_name="Punkt początkowy",
        help_text="Nazwa punktu początkowego odcinka.",
    )
    end_point_name = models.CharField(
        max_length=100,
        verbose_name="Punkt końcowy",
        help_text="Nazwa punktu końcowego odcinka.",
    )
    gpx_file = models.FileField(
        upload_to='gpx_files/%Y/%m/%d/',
        verbose_name="Plik GPX",
        help_text="Wgraj plik .gpx. Ścieżka zostanie wygenerowana automatycznie.",
        blank=True,
        null=True
    )
    gpx_path = gis_models.LineStringField(
        verbose_name="Ścieżka GPX (geometria)",
        help_text="Geometria trasy wygenerowana z pliku GPX. Pole niewymagane.",
        blank=True,
        null=True,
        spatial_index=True,
        editable=False,  # Ukrywamy to pole w podstawowym formularzu admina
        dim=3
    )
    sequence = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Kolejność",
        help_text="Kolejność odcinka w ramach wycieczki (1 = pierwszy).",
        db_index=True  # Dodany indeks dla sortowania
    )
    # Stylowanie linii
    stroke = models.BooleanField(
        default=True,  # Zmienione z False na True - domyślnie pokazuj linie
        verbose_name="Rysuj linię",
        help_text="Czy rysować linię na mapie."
    )
    color = models.CharField(
        choices=Color.choices,
        max_length=10,
        default=Color.BLUE,
        verbose_name="Kolor",
        help_text="Kolor linii na mapie."
    )
    weight = models.PositiveSmallIntegerField(
        default=3,  # Zwiększone z 1 na 3 dla lepszej widoczności
        verbose_name="Grubość",
        help_text="Grubość linii (1-10 pikseli).",
        validators=[MinValueValidator(1), MaxValueValidator(10)]  # Zwiększony zakres
    )
    line_cap = models.CharField(
        choices=LineCap.choices,  # noqa
        max_length=10,
        default=LineCap.ROUND,
        verbose_name="Zakończenie linii",
        help_text="Styl zakończenia linii.",
        db_column='lineCap'
    )
    line_join = models.CharField(
        choices=LineJoin.choices,  # noqa
        max_length=10,
        default=LineJoin.ROUND,
        verbose_name="Łączenie linii",
        help_text="Styl łączenia segmentów linii.",
        db_column='lineJoin'
    )
    dash_array = models.CharField(
        choices=DashArray.choices,  # noqa
        max_length=10,  # Zwiększone z 5 na 10 dla nowych opcji
        default=DashArray.SOLID,  # Zmienione domyślnie na linię ciągłą
        blank=True,  # Może być puste dla linii ciągłej
        verbose_name="Styl kreskowania",
        help_text="Wzór kreskowania linii.",
        db_column='dashArray'
    )
    dash_offset = models.CharField(
        choices=DashOffset.choices,  # noqa
        max_length=5,
        default=DashOffset.NONE,
        verbose_name="Przesunięcie kreskowania",
        help_text="Przesunięcie początku wzoru kreskowania.",
        db_column='dashOffset'
    )

    # Przechowujemy kopię nazwy pliku, aby wykryć zmiany
    _original_gpx_file = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dla nowych obiektów ustawiamy _original_gpx_file na None, aby wymusić parsowanie przy pierwszym zapisie
        if not self.pk:
            self._original_gpx_file = None
        else:
            # Dla istniejących obiektów używamy aktualnej wartości gpx_file jako _original_gpx_file
            self._original_gpx_file = self.gpx_file

    def clean(self):
        """Walidacja modelu przed zapisem."""
        super().clean()

        # Waliduj że jeśli jest plik GPX, musi być geometria
        if self.gpx_file and not self.gpx_path:
            raise ValidationError({
                'gpx_file': 'Nie udało się sparsować pliku GPX. '
                            'Sprawdź czy plik jest poprawny.'
            })

    def save(self, *args, **kwargs):
        from odznaki.services.trip_service import parse_gpx_to_linestring_and_stats
        
        # Sprawdzamy, czy gpx_path został już ustawiony (np. w teście)
        gpx_path_was_set = hasattr(self, 'gpx_path') and self.gpx_path is not None
        
        if not gpx_path_was_set:
            # Sprawdzamy, czy plik GPX został zmieniony lub czy to nowy obiekt
            is_new = not self.pk
            is_file_changed = (self._original_gpx_file is None) or (self.gpx_file != self._original_gpx_file)
            has_gpx_file = self.gpx_file is not None
            should_parse = has_gpx_file and (is_new or is_file_changed)
            
            # Jeśli mamy plik i należy go przetworzyć
            if should_parse:
                try:
                    # Funkcja zwraca krotkę (linestring, stats), ale używamy tylko linestring
                    linestring, _stats = parse_gpx_to_linestring_and_stats(self.gpx_file)
                    self.gpx_path = linestring
                except Exception as e:
                    # Logowanie błędu do konsoli serwera
                    import logging
                    logger = logging.getLogger('odznaki.models.trips')
                    logger.error(f"Błąd parsowania pliku GPX: {e}")
                    self.gpx_path = None
            # Jeśli nie mamy pliku i to nowy obiekt, ustawiamy gpx_path na None
            elif not has_gpx_file and is_new:
                self.gpx_path = None
            # W przeciwnym przypadku zachowujemy istniejącą wartość gpx_path

        # Zapisujemy obiekt
        super().save(*args, **kwargs)
        
        # Aktualizujemy oryginalną wartość pliku po zapisie
        self._original_gpx_file = self.gpx_file

    class Meta:
        db_table = 'odznaki_trip_segment'  # Konsekwentne nazewnictwo
        verbose_name = 'Odcinek GPX'
        verbose_name_plural = 'Odcinki GPX'
        ordering = ['trip', 'sequence']  # Sortowanie po wycieczce i kolejności
        unique_together = [['trip', 'sequence']]  # Zapewnia unikalność kolejności w ramach wycieczki
        indexes = [
            models.Index(fields=['trip', 'sequence']),
        ]

    def __str__(self):
        return f"Odcinek {self.sequence}: {self.start_point_name} → {self.end_point_name}"

    @property
    def leaflet_style(self):
        """
        Zwraca słownik stylów dla Leaflet na podstawie pól tego modelu.
        Logika została przeniesiona bezpośrednio tutaj z serwisu.
        """
        # Ta logika jest teraz bezpośrednio w modelu, co jest czystsze.
        return {
            'color': self.color,
            'weight': self.weight,
            'opacity': 1.0,
            'lineCap': self.line_cap,
            'lineJoin': self.line_join,
            'dashArray': self.dash_array or DashArray.SOLID,
            'dashOffset': self.dash_offset,
            'smoothFactor': 1.0,
            'stroke': self.stroke
        }

    @property
    def is_complete(self):
        """
        Sprawdza czy odcinek ma wszystkie wymagane dane.
        Logika została przeniesiona bezpośrednio tutaj z serwisu.
        """
        return all([
            bool(self.trip_id),
            bool(self.start_point_name),
            bool(self.end_point_name),
            bool(self.gpx_path)
        ])
