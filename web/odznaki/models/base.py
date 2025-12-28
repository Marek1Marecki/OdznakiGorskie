# odznaki/models/base.py

from django.db import models
from django.contrib.gis.db import models as gis_models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# Usunęliśmy globalny import, aby przerwać pętlę zależności
# from odznaki.utils import geo_helpers


class AbstractTimeStampedModel(models.Model):
    """Abstrakcyjny model bazowy dodający pola znaczników czasu."""
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data utworzenia",
        help_text="Data i czas utworzenia rekordu"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Data modyfikacji",
        help_text="Data i czas ostatniej modyfikacji rekordu"
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']


class LocationModel(AbstractTimeStampedModel):
    """Abstrakcyjny model bazowy dla wszystkich jednostek geograficznych."""
    name = models.CharField(
        max_length=100,
        blank=False,
        verbose_name="Nazwa",
        help_text="Nazwa lokalizacji (wymagana)"
    )
    translation = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Tłumaczenie",
        help_text="Tłumaczenie nazwy na inny język"
    )
    code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Kod",
        help_text="Kod identyfikacyjny lokalizacji (np. ISO, NUTS)"
    )
    link = models.URLField(
        max_length=200,
        blank=True,
        verbose_name="Link",
        help_text="Link do zewnętrznej strony z informacjami o lokalizacji"
    )
    shape = gis_models.MultiPolygonField(
        null=True,
        blank=True,
        verbose_name="Kształt",
        help_text="Kształt geograficzny lokalizacji (MultiPolygon)",
        db_index=True,
        srid=4326
    )

    class Meta:
        abstract = True
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['code']),
        ]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        """
        Zwraca kanoniczny URL do szczegółów obiektu.
        Ta metoda musi zostać zaimplementowana przez każdą klasę potomną.
        """
        raise NotImplementedError(
            f"Model {self.__class__.__name__} nie ma zaimplementowanej metody get_absolute_url()"
        )

    def save(self, *args, **kwargs) -> None:
        """
        Zapisuje model po wykonaniu walidacji.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        """
        Wykonuje walidację danych modelu.
        
        Raises:
            ValidationError: Jeśli dane są nieprawidłowe
        """
        super().clean()

        # Import lokalny, aby uniknąć problemów
        from odznaki.utils import geo_helpers

        # Walidacja geometrii
        if hasattr(self, 'shape') and self.shape is not None:
            errors = {}
            # Pobieramy błędy z funkcji walidacyjnej
            validation_errors = geo_helpers.validate_location_geometry(self.shape)
            
            # Jeśli są jakieś błędy, dodajemy je do słownika błędów
            if validation_errors:
                for field, error_list in validation_errors.items():
                    if field not in errors:
                        errors[field] = []
                    errors[field].extend(error_list)
            
            # Jeśli są jakieś błędy, rzucamy wyjątek
            if errors:
                raise ValidationError(errors)

    @property
    def has_geometry(self) -> bool:
        """
        Sprawdza czy lokalizacja ma zdefiniowany kształt geograficzny.
        """
        return self.shape is not None and not self.shape.empty