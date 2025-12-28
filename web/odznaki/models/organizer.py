from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from tinymce.models import HTMLField
from .base import AbstractTimeStampedModel
from odznaki.validators import validate_image_size

def organizer_decoration_path(instance, filename: str) -> str:
    """Generuje ścieżkę do zapisu zdjęcia odznaki klubowej organizatora."""
    return f'organizers/{instance.id}/decorations/{filename}'

class Organizer(AbstractTimeStampedModel):
    """Reprezentuje organizatora odznak (np. oddział PTTK)."""
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nazwa",
        help_text="Nazwa organizatora.",
        db_index=True
    )
    secondary_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Dodatkowa nazwa",
        help_text="Dodatkowa nazwa organizatora."
    )
    link = models.URLField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Link",
        help_text="Link do organizatora."
    )
    email = models.EmailField(
        max_length=100,
        blank=True,
        verbose_name="Email",
        help_text="Email organizatora."
    )
    address = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Adres",
        help_text="Adres organizatora."
    )
    date_of_accession = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data przystąpienia",
        help_text="Data przystąpienia do organizatora."
    )
    booklet_required = models.BooleanField(
        default=False,
        verbose_name="Książeczka wymagana?",
        help_text="Oznacza, czy organizator wymaga książeczki."
    )
    decoration_required = models.BooleanField(
        default=False,
        verbose_name="Czy wymagana odznaka klubowa?",
        help_text="Oznacza, czy organizator wymaga odznaki klubowej."
    )
    decoration_scan = models.ImageField(
        upload_to=organizer_decoration_path,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
            validate_image_size
        ],
        verbose_name="Zdjęcie odznaki klubowej",
        help_text="Zdjęcie odznaki klubowej."
    )
    statute = HTMLField(
        blank=True,
        verbose_name="Regulamin",
        help_text="Regulamin organizatora."
    )
    statute_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data regulaminu",
        help_text="Data regulaminu organizatora."
    )

    class Meta:
        db_table = 'odznaki_organizer'
        verbose_name = 'Organizator'
        verbose_name_plural = 'Organizatorzy'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]

    def clean(self):
        """
        Waliduje, że jeśli podano datę regulaminu, to musi być również podana treść regulaminu.
        """
        super().clean()
        
        errors = {}
        
        # Jeśli podano datę regulaminu, to treść regulaminu jest wymagana
        if self.statute_date and not self.statute:
            errors['statute'] = ['Treść regulaminu jest wymagana, jeśli podano datę.']
            
        # Jeśli podano treść regulaminu, to data regulaminu jest wymagana
        if self.statute and not self.statute_date:
            errors['statute_date'] = ['Data regulaminu jest wymagana, jeśli podano treść.']
            
        # Jeśli którykolwiek z warunków nie jest spełniony, zwracamy błąd dla obu pól
        if errors:
            # Upewniamy się, że oba pola są w słowniku błędów, jeśli którekolwiek jest nieprawidłowe
            if 'statute' in errors and 'statute_date' not in errors:
                errors['statute_date'] = []
            elif 'statute_date' in errors and 'statute' not in errors:
                errors['statute'] = []
                
            raise ValidationError(errors)

    def __str__(self):
        return self.name
