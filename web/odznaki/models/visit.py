# odznaki/models/visit.py
from django.db import models
from django.db.models import Q
from django.core.validators import MinValueValidator
from django.db.models.functions import Now
from tinymce.models import HTMLField

from .base import AbstractTimeStampedModel
from .point_of_interest import PointOfInterest
from .booklet import Booklet, BookletType
from odznaki.managers import VisitQuerySet

class Visit(AbstractTimeStampedModel):
    objects = VisitQuerySet.as_manager()
    
    point_of_interest = models.ForeignKey(
        PointOfInterest, 
        on_delete=models.PROTECT, 
        null=False, 
        blank=False, 
        related_name='visits', 
        related_query_name='visits',
        verbose_name="Punkt turystyczny", 
        help_text="Odwiedzony punkt turystyczny."
    )
    description = HTMLField(
        max_length=1000, 
        blank=True, 
        verbose_name="Opis", 
        help_text="Twoje notatki, wspomnienia lub informacje o potwierdzeniu zdobycia."
    )
    visit_date = models.DateField(
        blank=False, 
        null=False, 
        verbose_name="Data wizyty", 
        help_text="Data odwiedzenia punktu.", 
        db_index=True
    )
    got_booklet_number = models.PositiveSmallIntegerField(
        blank=True, 
        null=True, 
        verbose_name="Numer książeczki GOT", 
        help_text="Numer książeczki GOT ze zdobyciem obiektu.", 
        validators=[MinValueValidator(1)]
    )
    entry_on_page = models.PositiveSmallIntegerField(
        blank=True, 
        null=True, 
        verbose_name="Wpis na stronie", 
        help_text="Zdobycie wpisane na stronie.", 
        validators=[MinValueValidator(1)]
    )

    class Meta:
        db_table = 'odznaki_visit'
        verbose_name = 'Wizyta'
        verbose_name_plural = 'Wizyty'
        ordering = ['-visit_date', 'point_of_interest__name']
        indexes = [
            models.Index(fields=['visit_date']),
            models.Index(fields=['point_of_interest', 'visit_date']),
            models.Index(fields=['-visit_date']),
            models.Index(fields=['point_of_interest', '-visit_date'], name='visit_poi_latest_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(visit_date__lte=Now()), 
                name='visit_date_cannot_be_in_future',
                violation_error_message="Data wizyty nie może być w przyszłości."
            ),
            models.UniqueConstraint(
                fields=['point_of_interest', 'visit_date'], 
                name='unique_visit_per_poi_per_day',
                violation_error_message="Wizyta w tym punkcie już istnieje dla tej daty."
            )
        ]

    @property
    def related_got_booklet(self):
        """
        Zwraca obiekt Booklet dla numeru GOT podanego w tej wizycie,
        jeśli taki istnieje.
        """
        if self.got_booklet_number:
            try:
                return Booklet.objects.get(
                    booklet_type=BookletType.GENERAL_GOT,
                    sequence_number=self.got_booklet_number
                )
            except Booklet.DoesNotExist:
                return None
        return None

    def __str__(self) -> str:
        return f"{self.point_of_interest.name} - {self.visit_date}"
