# odznaki/models/badge_requirement.py
from django.db import models

from .base import AbstractTimeStampedModel
from .point_of_interest import PointOfInterest
# ZMIANA: Usunięto import 'Badge', aby przerwać pętlę
from odznaki.managers import BadgeRequirementManager

class BadgeRequirement(AbstractTimeStampedModel):
    objects = BadgeRequirementManager()
    
    # ZMIANA: Używamy 'Badge' jako stringa
    badge = models.ForeignKey(
        'Badge', 
        on_delete=models.PROTECT, 
        null=False, 
        blank=False, 
        related_name='badge_requirements', 
        related_query_name='badge_requirements',
        verbose_name="Odznaka", 
        help_text="Odznaka związana z punktem."
    )
    point_of_interest = models.ForeignKey(
        PointOfInterest, 
        on_delete=models.PROTECT, 
        null=False, 
        blank=False, 
        related_name='badge_requirements', 
        related_query_name='badge_requirement', 
        verbose_name="Punkt turystyczny", 
        help_text="Punkt turystyczny związany z odznaką."
    )
    obligatory = models.BooleanField(
        default=False, 
        verbose_name="Czy obowiązkowy?", 
        help_text="Oznacza czy obiekt jest obowiązkowy dla tej odznaki."
    )

    class Meta:
        db_table = 'odznaki_badge_requirement'
        verbose_name = 'Wymaganie odznaki'
        verbose_name_plural = 'Wymagania odznaki'
        unique_together = [['badge', 'point_of_interest']]
        ordering = ['badge__name', 'point_of_interest__name']
        indexes = [
            models.Index(fields=['badge']),
            models.Index(fields=['point_of_interest']),
            models.Index(fields=['badge', 'point_of_interest']),
        ]

    def __str__(self) -> str:
        # Używamy bezpośrednio ID zamiast odwołań do powiązanych obiektów
        # aby uniknąć potencjalnych problemów z importem cyklicznym
        return f"Wymaganie dla odznaki ID: {self.badge_id} - Punkt: {self.point_of_interest.name}"
