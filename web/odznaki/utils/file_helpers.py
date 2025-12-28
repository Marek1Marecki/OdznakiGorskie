"""Pomocnicze funkcje do obsługi plików.

Ten moduł zawiera funkcje pomocnicze do walidacji i przetwarzania
plików, szczególnie plików GPX używanych w aplikacji.
"""
import os
import uuid
import xml.etree.ElementTree as ET
from typing import Optional
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

def generate_unique_upload_path(instance, filename: str, subfolder: str = '') -> str:
    """
    Generuje unikalną i zorganizowaną ścieżkę dla przesyłanego pliku.

    Struktura: <nazwa_modelu>/<pk_instancji>/[subfolder/]<uuid>.<rozszerzenie>
    
    Zapewnia to, że każdy plik ma unikalną ścieżkę, eliminując ryzyko nadpisania.
    
    Args:
        instance: Instancja modelu, dla której generowana jest ścieżka
        filename: Oryginalna nazwa pliku
        subfolder: Opcjonalny podkatalog w strukturze ścieżki
        
    Returns:
        str: Unikalna ścieżka do zapisu pliku
    """
    class_name = instance.__class__.__name__.lower()
    instance_pk = instance.pk or 'new'  # 'new' dla obiektów, które nie mają jeszcze PK
    
    # Wyodrębnienie rozszerzenia pliku (z zachowaniem oryginalnej wielkości liter)
    _, ext = os.path.splitext(filename)
    
    # Generowanie unikalnej nazwy pliku z UUID
    unique_filename = f"{uuid.uuid4().hex}{ext.lower()}"
    
    # Budowanie ścieżki
    path_parts = [class_name, str(instance_pk)]
    if subfolder:
        path_parts.append(subfolder.strip('/'))
    path_parts.append(unique_filename)
    
    return os.path.join(*path_parts)


def booklet_upload_path(instance, filename):
    """
    Generuje unikalną ścieżkę dla plików książeczek (skanów i obrazów).
    Struktura: booklet/<pk>/<uuid>.<ext>
    """
    return generate_unique_upload_path(instance, filename)


def badge_image_upload_path(instance, filename):
    """
    Generuje unikalną ścieżkę dla obrazów stopni odznak.
    Struktura: badgelevel/<pk>/image/<uuid>.<ext>
    """
    return generate_unique_upload_path(instance, filename, subfolder='image')

def organizer_decoration_path(instance, filename):
    """
    Generuje unikalną ścieżkę dla zdjęcia odznaki klubowej organizatora.
    Struktura: organizer/<pk>/decoration/<uuid>.<ext>
    """
    return generate_unique_upload_path(instance, filename, subfolder='decoration')
