# odznaki/models/badge_news_item.py

from django.db import models
from .base import AbstractTimeStampedModel

class BadgeNewsItem(AbstractTimeStampedModel):
    """
    Model do przechowywania pojedynczej informacji o zmianie lub dodaniu odznaki,
    pobranej ze strony https://odznaki.org/zmiany/.
    """
    
    class ChangeType(models.TextChoices):
        ADDITION = 'ADD', 'Dodanie'
        CHANGE = 'CHG', 'Zmiana'

    change_type = models.CharField(
        max_length=3,
        choices=ChangeType.choices,
        verbose_name="Typ zmiany"
    )
    badge_name = models.CharField(
        max_length=255,
        verbose_name="Nazwa odznaki"
    )
    change_date_str = models.CharField(
        max_length=50,
        verbose_name="Data zmiany (tekstowo)"
    )
    is_dismissed = models.BooleanField(
        default=False,
        db_index=True,  # Dodajemy indeks, bo będziemy często po tym polu filtrować
        verbose_name="Czy ukryty?",
        help_text="Zaznacz, aby ukryć ten wpis na stronie głównej."
    )
    source_url = models.URLField(
        default="",
        verbose_name="URL źródłowy"
    )

    class Meta:
        db_table = 'odznaki_badge_news_item'
        verbose_name = 'Wiadomość o odznace'
        verbose_name_plural = 'Wiadomości o odznakach'
        ordering = ['-created_at'] # Domyślnie sortuj od najnowszych pobranych
        constraints = [
            models.UniqueConstraint(
                fields=['change_type', 'badge_name', 'change_date_str'],
                name='unique_news_item'
            )
        ]

    def __str__(self):
        return f"{self.change_date_str} - {self.badge_name} ({self.get_change_type_display()})"