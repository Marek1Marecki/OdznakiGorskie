# odznaki/services/booklet_service.py
import logging
from typing import List, Optional, Dict
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from odznaki.models.booklet import Booklet, BookletType
from odznaki.exceptions import ValidationError, BusinessLogicError


logger = logging.getLogger(__name__)


def validate_booklet(booklet: Booklet) -> None:
    """
    Wykonuje pełną walidację logiki biznesowej dla instancji Booklet,
    łącząc walidację z modelu i dodatkowe reguły biznesowe.
    """
    # Krok 1: Uruchomienie wbudowanych walidatorów Django (np. CheckConstraints z modelu)
    try:
        booklet.full_clean()
    except DjangoValidationError as e:
        # Jeśli podstawowa walidacja zawiedzie, od razu rzucamy wyjątek
        raise ValidationError("Błąd walidacji pól książeczki.", error_dict=e.message_dict) from e

    # Krok 2: Dodatkowe, niestandardowe reguły biznesowe
    errors = {}
    
    # Reguła 1: Logika dla pola 'sequence_number'
    if booklet.booklet_type == BookletType.GENERAL_GOT and booklet.sequence_number is None:
        errors['sequence_number'] = _("Numer kolejny jest wymagany dla książeczek typu 'Ogólna GOT'.")
    elif booklet.booklet_type != BookletType.GENERAL_GOT and booklet.sequence_number is not None:
        errors['sequence_number'] = _("Numer kolejny można podać tylko dla książeczek typu 'Ogólna GOT'.")
    
    # Reguła 2: Logika dla pola 'organizer'
    if booklet.booklet_type == BookletType.ORGANIZER and not booklet.organizer:
        errors['organizer'] = _("Organizator jest wymagany dla książeczek typu 'Organizatora'.")
    elif booklet.booklet_type != BookletType.ORGANIZER and booklet.organizer is not None:
        # Ta reguła zapobiega przypisaniu organizatora do książeczki, która nie jest typu "Organizatora"
        errors['organizer'] = _("Organizatora można powiązać tylko z książeczką typu 'Organizatora'.")
    
    # Reguła 3: Walidacja unikalności numeru kolejnego (tylko dla GOT)
    if booklet.booklet_type == BookletType.GENERAL_GOT and booklet.sequence_number is not None:
        query = Booklet.objects.filter(
            booklet_type=BookletType.GENERAL_GOT,
            sequence_number=booklet.sequence_number
        )
        if booklet.pk:
            query = query.exclude(pk=booklet.pk)
        if query.exists():
            errors['sequence_number'] = _("Istnieje już książeczka GOT o tym numerze kolejnym.")

    if errors:
        raise ValidationError("Błąd walidacji danych książeczki.", error_dict=errors)


@transaction.atomic
def create_or_update_booklet(booklet: Booklet, update_fields: Optional[List[str]] = None) -> Booklet:
    """
    Centralna, bezpieczna funkcja do tworzenia i aktualizowania książeczek.
    """
    try:
        validate_booklet(booklet)
        # Model jest już "czysty", więc nie ma ryzyka rekurencji.
        # Przekazujemy 'update_fields' do metody save dla optymalizacji.
        booklet.save(update_fields=update_fields)
        logger.info(f"Zapisano książeczkę: '{booklet.name}' (ID: {booklet.id})")
        return booklet
    except (ValidationError, BusinessLogicError):
        # Przekazujemy dalej nasze własne, oczekiwane wyjątki.
        raise
    except Exception as e:
        # Wszystkie inne, nieoczekiwane błędy logujemy i opakowujemy.
        logger.error(f"Nieoczekiwany błąd podczas zapisywania książeczki {getattr(booklet, 'name', '')}: {str(e)}")
        raise BusinessLogicError(
            "Wystąpił nieoczekiwany błąd podczas zapisywania książeczki."
        ) from e
