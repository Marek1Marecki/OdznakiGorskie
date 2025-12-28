# odznaki/models/booklet.py

from django.db import models
from django.db.models import Q, F
from django.urls import reverse

from .base import AbstractTimeStampedModel
from .organizer import Organizer
from odznaki.validators import validate_image_size, validate_file_size
from django.core.validators import FileExtensionValidator

def booklet_upload_path(instance, filename: str) -> str:
    """Generuje ścieżkę do zapisu plików dla książeczki."""
    return f'booklets/{instance.id}/{filename}'


class BookletType(models.TextChoices):
    """Dostępne typy książeczek do potwierdzeń."""
    GENERAL_GOT = 'got', 'Ogólna GOT'
    ORGANIZER = 'organizer', 'Organizatora'
    BADGE_SPECIFIC = 'badge', 'Dedykowana do odznaki'


class Booklet(AbstractTimeStampedModel):
    """Reprezentuje fizyczną lub wirtualną książeczkę do potwierdzeń."""
    
    name = models.CharField(
        max_length=100,
        verbose_name="Nazwa książeczki",
        help_text="Oficjalna nazwa dla tej książeczki.",
    )
    club_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Numer klubowy",
        help_text="Numer klubowy książeczki.",
    )
    booklet_type = models.CharField(
        max_length=20,
        choices=BookletType.choices,
        default=BookletType.GENERAL_GOT,
        verbose_name="Typ książeczki",
        help_text="Typ książeczki.",
    )
    sequence_number = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Numer kolejny",
        help_text="Numer kolejny książeczki.",
    )
    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booklets',
        verbose_name="Organizator"
    )
    is_required = models.BooleanField(
        default=False,
        verbose_name="Czy książeczka jest wymagana?",
        help_text="Oznacza, czy organizator wymaga książeczki."
    )
    is_possessed = models.BooleanField(
        default=False,
        verbose_name="Czy książeczka posiadana?",
        help_text="Oznacza, czy posiadam książeczkę."
    )
    scan = models.FileField(
        upload_to=booklet_upload_path,
        blank=True,
        null=True,
        verbose_name="Skan książeczki PDF",
        help_text="Skan książeczki w formacie PDF.",
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf']),
            validate_file_size
        ]
    )
    scan_date = models.DateField(
        blank=True,
        null=True,
        help_text="Ostatnia data wykonania skanu PDF."
    )
    image = models.ImageField(
        upload_to=booklet_upload_path,
        blank=True,
        null=True,
        verbose_name="Zdjęcie książeczki",
        help_text="Zdjęcie książeczki.",
        validators=[validate_image_size]
    )
    valid_from = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data ważności od",
        help_text="Data ważności książeczki od."
    )
    valid_to = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data ważności do",
        help_text="Data ważności książeczki do."
    )
    
    class Meta:
        verbose_name = 'Książeczka'
        verbose_name_plural = 'Książeczki'
        ordering = ['name']
        constraints = [
            models.CheckConstraint(
                condition=Q(valid_from__isnull=True) | Q(valid_to__isnull=True) | Q(valid_to__gte=F('valid_from')),
                name='check_booklet_valid_to_after_valid_from'
            ),
        ]

    def get_absolute_url(self):
        """Zwraca kanoniczny URL do strony szczegółowej tej książeczki."""
        return reverse('odznaki:booklet-detail', kwargs={'pk': self.pk})

    def __str__(self):
        if self.booklet_type == BookletType.GENERAL_GOT and self.sequence_number:
            return f"{self.name} (GOT #{self.sequence_number})"
        return self.name
