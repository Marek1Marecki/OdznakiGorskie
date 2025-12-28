# odznaki/models/badge.py

from django.db import models
from django.db.models import Q, F
from django.core.validators import MinValueValidator
from tinymce.models import HTMLField
from .base import AbstractTimeStampedModel
# ZMIANA: Importujemy modele z ich nowych, dedykowanych plików
from .booklet import Booklet
from .organizer import Organizer
from .point_of_interest import PointOfInterest
# ZMIANA: Usunięto import 'BadgeRequirement', aby przerwać pętlę


class Badge(AbstractTimeStampedModel):
    """Model reprezentujący odznakę turystyczną."""
    
    name = models.CharField(
        max_length=100,
        verbose_name="Nazwa odznaki",
        help_text="Pełna, oficjalna nazwa odznaki turystycznej.",
        blank=False,
        unique=True,
    )
    required_poi_count = models.SmallIntegerField(
        verbose_name="Liczba wymaganych obiektów",
        help_text="Minimalna liczba punktów POI, które trzeba zdobyć, aby zaliczyć odznakę.",
        blank=False,
        validators=[MinValueValidator(1)],
        error_messages={
            'invalid': 'Liczba wymaganych obiektów musi być liczbą całkowitą'
        }
    )
    total_poi_count = models.SmallIntegerField(
        verbose_name="Ilość obiektów do wyboru",
        help_text="Całkowita liczba punktów POI dostępnych do wyboru w ramach odznaki.",
        blank=False,
        validators=[MinValueValidator(1)],
        error_messages={
            'invalid': 'Ilość obiektów do wyboru musi być liczbą całkowitą'
        }
    )
    link = models.URLField(
        max_length=200, 
        blank=True, 
        verbose_name="Link", 
        help_text="Link do oficjalnej strony internetowej odznaki."
    )
    start_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data rozpoczęcia",
        help_text="Data rozpoczęcia zdobywania obiektów do odznaki."
    )
    end_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data zakończenia",
        help_text="Data zakończenia zdobywania obiektów do odznaki."
    )
    statute_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data regulaminu",
        help_text="Data regulaminu odznaki."
    )
    organizer = models.ForeignKey(
        Organizer, # ZMIANA: Usunięto cudzysłów
        on_delete=models.SET_NULL,
        related_name='badges',
        related_query_name='badge',
        blank=True,
        null=True,
        verbose_name="Organizator",
        help_text="Organizator odznaki."
    )
    statute = HTMLField(
        blank=True, 
        verbose_name="Regulamin", 
        help_text="Regulamin odznaki."
    )
    establishment_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data ustanowienia",
        help_text="Data ustanowienia odznaki."
    )
    statute_link = models.URLField(
        max_length=200,
        blank=True,
        verbose_name="Link do regulaminu",
        help_text="Link do strony z oficjalnym regulaminem."
    )
    booklet = models.ForeignKey(
        Booklet, # ZMIANA: Usunięto cudzysłów
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='associated_badges',
        related_query_name='badge',
        verbose_name="Książeczka",
        help_text="Książeczka związana z odznaką.",
        limit_choices_to={'booklet_type__in': ['badge', 'got']},
    )
    points_of_interest = models.ManyToManyField(
        PointOfInterest, 
        through='BadgeRequirement',
        through_fields=('badge', 'point_of_interest'),
        verbose_name='Punkty turystyczne',
        help_text='Lista punktów turystycznych przypisanych do odznaki.'
    )
    is_fully_achieved = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Czy odznaka jest w pełni zdobyta",
        help_text="Status obliczany automatycznie. Oznacza, że wszystkie warunki zdobycia odznaki zostały spełnione."
    )

    class Meta:
        db_table = 'odznaki_badge'
        verbose_name = 'Odznaka'
        verbose_name_plural = 'Odznaki'
        ordering = ['name']
        constraints = [
            models.CheckConstraint(
                condition=Q(start_date__isnull=True) | Q(end_date__isnull=True) | Q(end_date__gte=F('start_date')),
                name='check_badge_end_date_after_start_date',
                violation_error_message = "Data końca musi być późniejsza lub równa dacie startu."
            ),
            models.CheckConstraint(
                condition=Q(required_poi_count__lte=F('total_poi_count')),
                name='check_badge_required_lte_to_choose',
                violation_error_message="Liczba wymaganych POI nie może być większa niż całkowita liczba POI."
            )
        ]
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['organizer', 'name']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['is_fully_achieved', 'organizer'], name='badge_status_org_idx'),
            models.Index(fields=['is_fully_achieved', 'start_date'], name='badge_status_date_idx'),
            models.Index(fields=['is_fully_achieved', 'end_date'], name='badge_status_end_idx'),
        ]

    @property
    def is_active(self) -> bool:
        """Sprawdza, czy odznaka jest aktualnie aktywna na podstawie dat."""
        from datetime import date
        today = date.today()

        if self.start_date and self.start_date > today:
            return False

        if self.end_date and self.end_date < today:
            return False

        return True

    def __str__(self) -> str:
        return self.name
