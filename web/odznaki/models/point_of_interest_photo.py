# odznaki/models/point_of_interest_photo.py
from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.files.storage import default_storage

from .base import AbstractTimeStampedModel
from .point_of_interest import PointOfInterest
from odznaki.validators import validate_image_size

def picture_upload_path(instance, filename: str) -> str:
    return f'poi_photos/{instance.point_of_interest.id}/{filename}'

class PointOfInterestPhoto(AbstractTimeStampedModel):
    point_of_interest = models.ForeignKey(
        PointOfInterest, 
        on_delete=models.CASCADE, 
        blank=False, 
        null=False, 
        related_name='photos', 
        related_query_name='photo', 
        verbose_name="Punkt turystyczny", 
        help_text="Punkt turystyczny powiązany ze zdjęciem."
    )
    picture = models.ImageField(
        upload_to=picture_upload_path, 
        blank=False, 
        verbose_name="Zdjęcie", 
        help_text="Plik zdjęcia.", 
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']), 
            validate_image_size
        ]
    )
    description = models.CharField(
        max_length=200, 
        blank=True, 
        default="", 
        verbose_name="Opis", 
        help_text="Opis zdjęcia."
    )
    photo_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data wykonania zdjęcia",
        help_text="Opcjonalnie: podaj datę wykonania zdjęcia, aby powiązać je z konkretną wizytą."
    )

    class Meta:
        db_table = 'odznaki_point_of_interest_photo'
        verbose_name = 'Zdjęcie punktu turystycznego'
        verbose_name_plural = 'Zdjęcia punktów turystycznych'
        ordering = ['-photo_date', 'point_of_interest__name'] 
        indexes = [
            models.Index(fields=['point_of_interest']),
            models.Index(fields=['photo_date']), 
        ]

    def __str__(self):
        try:
            if hasattr(self, 'id') and self.id and hasattr(self, 'point_of_interest') and self.point_of_interest:
                return f'Zdjęcie {self.id} - {self.point_of_interest.name}'
        except PointOfInterest.DoesNotExist:
            pass
        return 'Nowe zdjęcie'
        
    def delete(self, *args, **kwargs):
        """Usuwa plik ze storage przed usunięciem rekordu."""
        if self.picture:
            if default_storage.exists(self.picture.name):
                default_storage.delete(self.picture.name)
        super().delete(*args, **kwargs)
