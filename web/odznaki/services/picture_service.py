# odznaki/services/picture_service.py

import logging
from typing import List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import UploadedFile

from odznaki.models.point_of_interest_photo import PointOfInterestPhoto
from odznaki.models.point_of_interest import PointOfInterest
from odznaki.exceptions import ValidationError

logger = logging.getLogger(__name__)


@transaction.atomic
def create_photo_for_poi(
    point_of_interest: PointOfInterest,
    picture_file: UploadedFile,
    description: str = ""
) -> PointOfInterestPhoto:
    """
    Centralna, bezpieczna funkcja do tworzenia i zapisywania zdjęcia
    dla danego punktu turystycznego.
    """
    photo = PointOfInterestPhoto(
        point_of_interest=point_of_interest,
        picture=picture_file,
        description=description
    )
    
    try:
        # Używamy wbudowanej walidacji z modelu (sprawdza m.in. rozszerzenie i rozmiar pliku)
        photo.full_clean()
    except DjangoValidationError as e:
        raise ValidationError("Błąd walidacji danych zdjęcia.", error_dict=e.message_dict) from e
        
    photo.save()
    logger.info(f"Utworzono nowe zdjęcie (ID: {photo.id}) dla punktu '{point_of_interest.name}'")
    
    return photo


@transaction.atomic
def delete_photo(photo: PointOfInterestPhoto) -> None:
    """
    Bezpiecznie usuwa obiekt zdjęcia z bazy danych.
    Powiązany plik jest usuwany automatycznie dzięki sygnałom Django.
    """
    photo_id = photo.id
    # Bezpieczne pobranie nazwy POI, nawet jeśli obiekt został już usunięty
    poi_name = getattr(photo.point_of_interest, 'name', 'N/A')
    photo.delete()
    logger.info(f"Usunięto zdjęcie (ID: {photo_id}) z punktu '{poi_name}'")
