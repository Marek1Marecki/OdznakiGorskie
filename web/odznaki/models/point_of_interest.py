# odznaki/models/point_of_interest.py
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.urls import reverse

from .base import AbstractTimeStampedModel
from .geography import MesoRegion, Voivodeship, Country, Province, SubProvince, MacroRegion
from odznaki.managers import PointOfInterestQuerySet

class PointOfInterest(AbstractTimeStampedModel):
    objects = PointOfInterestQuerySet.as_manager()
    
    class Category(models.TextChoices):
        PEAK = 'peak', 'Szczyt'
        TOWER = 'tower', 'Wieża'
        PLATFORM = 'platform', 'Platforma'
        SHELTER = 'shelter', 'Schronisko'
        CROSS = 'cross', 'Krzyż'
        LAKE = 'lake', 'Staw'
        PANORAMA = 'panorama', 'Panorama'
        VALLEY = 'valley', 'Dolina'
        WATERFALL = 'waterfall', 'Wodospad'
        CEMETERY = 'cemetery', 'Cmentarz'
        BUILDING = 'building', 'Budynek'
        PASS = 'pass', 'Przełęcz'
        OTHER = 'other', 'Inne'

    name = models.CharField(
        max_length=100,
        blank=False,
        verbose_name="Nazwa",
        help_text="Główna nazwa punktu (np. szczytu, schroniska)."
    )
    secondary_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Druga nazwa",
        help_text="Alternatywna nazwa punktu."
    )
    location = gis_models.PointField(
        blank=True,
        null=True,
        verbose_name="Lokalizacja",
        help_text="Lokalizacja obiektu.",
        db_index=True
    )
    height = models.PositiveIntegerField(
        'wysokość',
        null=True,
        blank=True,
        help_text='Wysokość w metrach nad poziomem morza.'
    )
    category = models.CharField(
        max_length=20,
        blank=False,
        choices=Category.choices,
        default=Category.PEAK,
        verbose_name="Typ obiektu",
        help_text="Wybierz kategorię tego punktu.",
        db_index=True
    )
    code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Kod",
        help_text="Unikalny kod identyfikacyjny (jeśli istnieje).",
        unique=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Czy istnieje?",
        help_text="Oznacza, czy obiekt istnieje.",
        db_index=True
    )
    mesoregion = models.ForeignKey(
        MesoRegion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='points_of_interest',
        related_query_name='point_of_interest',
        verbose_name="MesoRegion",
        help_text="MesoRegion, w którym leży ten obiekt."
    )
    voivodeship = models.ForeignKey(
        Voivodeship,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='points_of_interest_admin',  # Inna nazwa, aby uniknąć konfliktu
        verbose_name="Województwo (adm.)",
        help_text="Województwo administracyjne, w którym leży obiekt."
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='points_of_interest_country',
        verbose_name="Kraj (adm.)"
    )
    link = models.URLField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Link",
        help_text="Link do strony o tym obiekcie."
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Obiekt nadrzędny",
        help_text="Obiekt nadrzędny.",
        related_name='children'
    )
    province = models.ForeignKey(
        Province,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Prowincja (zdenormalizowana)",
        editable=False,
        db_index=True
    )
    subprovince = models.ForeignKey(
        SubProvince,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Podprowincja (zdenormalizowana)",
        editable=False,
        db_index=True
    )
    macroregion = models.ForeignKey(
        MacroRegion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Makroregion (zdenormalizowany)",
        editable=False,
        db_index=True
    )

    class Meta:
        db_table = 'odznaki_point_of_interest'
        ordering = ['-height', 'name']
        verbose_name = 'Punkt turystyczny'
        verbose_name_plural = 'Punkty turystyczne'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['height']),
            models.Index(fields=['mesoregion', 'category']),
            models.Index(fields=['-height', 'name'], name='poi_height_name_idx'),
            models.Index(fields=['voivodeship']),
            models.Index(fields=['country']),
            models.Index(fields=['parent']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['code'],
                condition=models.Q(code__isnull=False),
                name='unique_object_code_if_not_null'
            )
        ]

    def save(self, *args, **kwargs):
        """
        Automatycznie wypełnia pola hierarchii przed zapisem.

        OPTYMALIZACJA: Jeśli zapisujesz wiele POI, użyj select_related:
        pois = PointOfInterest.objects.select_related(
            'mesoregion__macroregion__subprovince__province__country'
        )
        for poi in pois:
            poi.some_field = new_value
            poi.save()  # Teraz bez dodatkowych queries
        """
        if self.mesoregion:
            # Sprawdź czy mamy już załadowane relacje (przez select_related)
            try:
                # Próbujemy dostać się do relacji bez triggerowania query
                macroregion = self.mesoregion.macroregion
                if macroregion:
                    self.macroregion = macroregion
                    subprovince = macroregion.subprovince
                    if subprovince:
                        self.subprovince = subprovince
                        province = subprovince.province
                        if province:
                            self.province = province
                            if province.country:
                                self.country = province.country
            except AttributeError:
                # Jeśli relacje nie są załadowane, loguj warning
                import logging
                logger = logging.getLogger('odznaki.models')
                logger.warning(
                    f"POI {self.pk}: Saving without select_related - "
                    "this will cause additional queries. "
                    "Use: .select_related('mesoregion__macroregion__subprovince__province__country')"
                )
        else:
            # Jeśli usunięto Mezoregion, wyczyść zdenormalizowane pola
            self.macroregion = None
            self.subprovince = None
            self.province = None

        super().save(*args, **kwargs)

    @property
    def full_name(self) -> str:
        """Zwraca pełną nazwę obiektu (główna + opcjonalna druga nazwa)."""
        if self.secondary_name:
            return f"{self.name} / {self.secondary_name}"
        return self.name

    @property
    def formatted_height(self) -> str:
        """Formatuje wysokość obiektu z jednostką."""
        if self.height is not None:
            return f"{self.height} m n.p.m."
        return "Wysokość nieznana"

    @property
    def representation(self) -> str:
        """Zwraca czytelną, tekstową reprezentację punktu POI."""
        height_str = f"({self.formatted_height})" if self.height is not None else ""
        mesoregion_str = self.mesoregion.name if self.mesoregion else 'Brak przypisania'
        return f"{self.full_name} {height_str} - {mesoregion_str}".strip()

    @property
    def visit_stats(self) -> dict:
        """Pobiera statystyki wizyt (Visit) dla danego punktu POI."""
        visits = self.visits.all()
        last_visit = visits.order_by('-visit_date').first()
        return {
            'visit_count': visits.count(),
            'last_visited_date': last_visit.visit_date if last_visit else None,
        }

    @property
    def has_visits(self) -> bool:
        """Sprawdza, czy punkt został kiedykolwiek odwiedzony."""
        # To jest znacznie bardziej wydajne niż .exists() jeśli mamy już prefetched 'visits'
        if hasattr(self, '_prefetched_objects_cache') and 'visits' in self._prefetched_objects_cache:
            return len(self._prefetched_objects_cache['visits']) > 0
        return self.visits.exists()

    def get_absolute_url(self) -> str:
        """Zwraca poprawny URL do strony szczegółowej tego POI."""
        # Używamy poprawnej nazwy URL ('poi-detail') i poprawnego argumentu ('poi_id')
        return reverse('odznaki:poi-detail', kwargs={'poi_id': self.pk})

    def __str__(self) -> str:
        details = []
        if self.height:
            details.append(f"{self.height}m")

        # Używamy self.get_category_display(), aby uzyskać czytelną nazwę
        details.append(self.get_category_display())

        return f"{self.name} ({', '.join(details)})"
