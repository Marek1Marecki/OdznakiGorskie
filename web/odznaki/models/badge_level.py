# odznaki/models/badge_level.py

from django.db import models
from django.db.models import Q, F
from django.core.validators import MinValueValidator, FileExtensionValidator

from .base import AbstractTimeStampedModel
# ZMIANA: Model Badge jest teraz w osobnym pliku
from .badge import Badge


def badge_image_upload_path(instance, filename: str) -> str:
    """Generuje ścieżkę do zapisu zdjęcia odznaki."""
    # Instance to BadgeLevel, więc dostęp do badge.id jest poprawny
    return f'badge_levels/{instance.badge.id}/{filename}'


class BadgeLevel(AbstractTimeStampedModel):
    """Model reprezentujący poziomy (stopnie) odznaki turystycznej."""
    
    class LevelType(models.TextChoices):
        JEDNOSTOPNIOWA = 'jednostopniowa', 'Jednostopniowa'
        POPULARNA = 'popularna', 'Popularna'
        BRAZOWA = 'brazowa', 'Brązowa'
        SREBRNA = 'srebrna', 'Srebrna'
        ZLOTA = 'zlota', 'Złota'
        PLATYNOWA = 'platynowa', 'Platynowa'
        DIAMENTOWA = 'diamentowa', 'Diamentowa'
        BRYLANTOWA = 'brylantowa', 'Brylantowa'
        MALA = 'mala', 'Mała'
        DUZA = 'duza', 'Duża'
        WIELKA = 'wielka', 'Wielka'
        PODSTAWOWA = 'podstawowa', 'Podstawowa'
        GLOWNA = 'glowna', 'Główna'
        MALA_POPULARNA = 'mala_popularna', 'Mała popularna'
        MALA_BRAZOWA = 'mala_brazowa', 'Mała brązowa'
        ZA_WYTRWALOSC = 'za_wytrwalosc', 'Za Wytrwałość'

    level = models.CharField(
        max_length=20,
        choices=LevelType.choices,
        default=LevelType.JEDNOSTOPNIOWA,
        verbose_name="Stopień odznaki",
        help_text="Wybierz stopień odznaki z dostępnej listy."
    )
    poi_count = models.SmallIntegerField(
        verbose_name="Liczba obiektów w stopniu",
        validators=[MinValueValidator(1)],
        help_text="Liczba punktów POI wymagana do zdobycia tego stopnia."
    )
    is_cumulative = models.BooleanField(
        default=False,
        verbose_name="Czy to część całości?",
        help_text="Czy odznaka jest częścią całości?"
    )
    image = models.ImageField(
        upload_to=badge_image_upload_path,
        blank=True,
        null=True,
        verbose_name="Zdjęcie odznaki",
        help_text="Grafika reprezentująca ten stopień odznaki.",
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
        ],
        height_field='image_height',
        width_field='image_width'
    )
    sent_at = models.DateField(
        default=None,
        blank=True,
        null=True,
        verbose_name="Data wysłania do weryfikacji"
    )
    verified_at = models.DateField(
        default=None,
        blank=True,
        null=True,
        verbose_name="Data weryfikacji"
    )
    received_at = models.DateField(
        default=None,
        blank=True,
        null=True,
        verbose_name="Data otrzymania odznaki"
    )
    collected_at = models.DateField(
        default=None,
        blank=True,
        null=True,
        verbose_name="Data wpięcia do albumu"
    )
    image_height = models.IntegerField(blank=True, null=True)
    image_width = models.IntegerField(blank=True, null=True)
    badge = models.ForeignKey(
        Badge, # ZMIANA: Usunięto cudzysłów
        on_delete=models.CASCADE,
        related_name='levels',
        verbose_name="Odznaka"
    )
    order = models.SmallIntegerField(
        default=0,
        verbose_name="Numer",
        help_text="Kolejność wyświetlania stopni. Musi być unikalna w obrębie jednej odznaki."
    )

    class Meta:
        db_table = 'odznaki_badge_level'
        verbose_name = 'Poziom odznaki'
        verbose_name_plural = 'Poziomy odznaki'
        ordering = ['badge', 'order']
        unique_together = [['badge', 'level']]
        indexes = [
            models.Index(fields=['badge', 'order'])
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(verified_at__gte=F('sent_at')) | Q(verified_at__isnull=True) | Q(sent_at__isnull=True),
                name='badgelevel_verified_after_sent'
            ),
            models.CheckConstraint(
                condition=Q(received_at__gte=F('verified_at')) | Q(received_at__isnull=True) | Q(verified_at__isnull=True),
                name='badgelevel_received_after_verified'
            ),
            models.CheckConstraint(
                condition=Q(collected_at__gte=F('received_at')) | Q(collected_at__isnull=True) | Q(received_at__isnull=True),
                name='badgelevel_collected_after_received'
            ),
            models.UniqueConstraint(
                fields=['badge', 'order'],
                name='unique_order_per_badge',
                violation_error_message='Kolejność musi być unikalna w obrębie odznaki.'
            )
        ]

    @property
    def status(self) -> str:
        """Zwraca aktualny status, delegując logikę do serwisu."""
        from odznaki.services import badge_level_service
        return badge_level_service.get_badge_level_status(self)

    def __str__(self) -> str:
        """Zwraca podstawową reprezentację poziomu odznaki."""
        return f"{self.badge.name} - {self.get_level_display()}"
        
    def clean(self):
        """
        Wykonuje walidację danych przed zapisem.
        Sprawdza m.in. poprawność kolejności dat.
        """
        from odznaki.services.badge_level_service import validate_badge_level
        from odznaki.exceptions import DatesNotInSequenceError
        
        # Sprawdzamy kolejność dat
        dates = [
            ('sent_at', self.sent_at),
            ('verified_at', self.verified_at),
            ('received_at', self.received_at),
            ('collected_at', self.collected_at)
        ]
        
        # Usuwamy puste wartości
        dates = [(name, date) for name, date in dates if date is not None]
        
        # Sprawdzamy, czy daty są posortowane rosnąco
        for i in range(len(dates) - 1):
            name1, date1 = dates[i]
            name2, date2 = dates[i+1]
            if date1 > date2:
                error_msg = f"Data w polu '{name2}' nie może być wcześniejsza niż w polu '{name1}'."
                raise DatesNotInSequenceError(
                    error_msg,
                    error_dict={name2: error_msg}
                )
        
        # Wywołujemy walidację z serwisu
        try:
            validate_badge_level(self)
        except Exception as e:
            if hasattr(e, 'error_dict'):
                from django.core.exceptions import ValidationError
                raise ValidationError(e.error_dict) from e
            raise

    @property
    def formatted_level(self) -> str:
        """Zwraca sformatowaną nazwę poziomu odznaki z użyciem serwisu."""
        from odznaki.services import badge_level_service
        return badge_level_service.format_badge_level(self.level)
