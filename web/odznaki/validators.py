# odznaki/validators.py
from django.core.exceptions import ValidationError

def validate_file_size(value):
    """Sprawdza, czy rozmiar przesyłanego pliku nie przekracza określonego
    limitu."""
    # Ustawiamy limit na 5MB
    limit = 5 * 1024 * 1024
    if value.size > limit:
        raise ValidationError(f'Plik jest zbyt duży. Rozmiar nie może przekraczać {limit/1024/1024:.1f} MB.')

def validate_image_size(value):
    """Sprawdza, czy rozmiar przesyłanego obrazu nie przekracza określonego
    limitu."""
    # Ustawiamy mniejszy limit na 2MB dla obrazów
    limit = 2 * 1024 * 1024
    if value.size > limit:
        raise ValidationError(f'Obraz jest zbyt duży. Rozmiar nie może przekraczać {limit/1024/1024:.1f} MB.')
