# odznaki/services/scraping_service.py

import requests
from bs4 import BeautifulSoup
import logging
from django.db import transaction

# Importujemy nasz model, do którego będziemy zapisywać dane
from odznaki.models import BadgeNewsItem

# Ustawienie loggera do śledzenia postępów i ewentualnych błędów
logger = logging.getLogger(__name__)

# Stała przechowująca URL, aby łatwo go zmienić w przyszłości
SOURCE_URL = "https://odznaki.org/zmiany/"


def get_page_content(url, timeout=10):
    """
    Pobiera zawartość strony z podanego URL.
    Wydzielona funkcja dla łatwiejszego testowania.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


def parse_badge_news_html(html_content):
    """
    Parsuje HTML i zwraca listę słowników z danymi o odznakach.
    Wydzielona funkcja dla łatwiejszego testowania.
    """
    soup = BeautifulSoup(html_content, 'lxml')

    # Znajdź główny kontener z listą zmian
    header = soup.find('h2', string='Ostatnie 50 zmian')
    if not header:
        logger.warning("Nie znaleziono nagłówka 'Ostatnie 50 zmian' na stronie. Struktura mogła się zmienić.")
        return []

    # Lista `<ul>` jest następnym elementem po nagłówku `<h2>`
    news_list = header.find_next_sibling('ul')
    if not news_list:
        logger.warning("Nie znaleziono listy 'ul' po nagłówku 'Ostatnie 50 zmian'. Struktura mogła się zmienić.")
        return []

    items = []
    for item in news_list.find_all('li'):
        # Tekst ikony mówi nam, czy to dodanie czy zmiana
        icon_span = item.find('span', class_='material-icons')
        if not icon_span:
            logger.warning(f"Nieprawidłowy format elementu - brak ikony: {item}")
            continue

        change_type_text = icon_span.get_text(strip=True)

        # Link <a> zawiera nazwę odznaki
        link_tag = item.find('a')
        if not link_tag:
            logger.warning(f"Nieprawidłowy format elementu - brak linku: {item}")
            continue

        badge_name_str = link_tag.get_text(strip=True).replace(':', '')

        # Data jest pierwszym tekstem w elemencie <li>
        full_text = item.get_text(" ", strip=True)
        try:
            date_str = full_text.split('-')[0].strip()
        except IndexError:
            logger.warning(f"Nie udało się wyodrębnić daty z tekstu: '{full_text}'")
            continue

        # Mapujemy tekst ikony na wartości z naszego modelu
        change_type_enum = None
        if 'add_circle' in change_type_text:
            change_type_enum = BadgeNewsItem.ChangeType.ADDITION
        elif 'change_circle' in change_type_text:
            change_type_enum = BadgeNewsItem.ChangeType.CHANGE

        if date_str and change_type_enum and badge_name_str:
            items.append({
                'change_date_str': date_str,
                'change_type': change_type_enum,
                'badge_name': badge_name_str,
                'source_url': "https://odznaki.org" + link_tag.get('href', '')
            })

    return items


def save_badge_news_items(items):
    """
    Zapisuje elementy do bazy danych.
    Zwraca liczbę nowo utworzonych elementów.
    """
    new_items_count = 0

    for item_data in items:
        try:
            with transaction.atomic():
                obj, created = BadgeNewsItem.objects.get_or_create(
                    change_date_str=item_data['change_date_str'],
                    change_type=item_data['change_type'],
                    badge_name=item_data['badge_name'],
                    defaults={'source_url': item_data['source_url']}
                )

                if created:
                    new_items_count += 1
                    logger.info(f"Dodano nowy wpis: {obj}")

        except Exception as e:
            logger.error(f"Błąd podczas zapisu wpisu '{item_data['badge_name']}' do bazy. Błąd: {e}")

    return new_items_count


def scrape_badge_news():
    """
    Pobiera dane ze strony odznaki.org/zmiany/, parsuje je
    i zapisuje nowe wpisy do bazy danych.

    Zwraca liczbę nowo dodanych wpisów.
    """
    logger.info("Rozpoczynam proces scrapingu wiadomości o odznakach z %s...", SOURCE_URL)

    try:
        # Krok 1: Pobierz zawartość strony
        html_content = get_page_content(SOURCE_URL)

    except requests.exceptions.RequestException as e:
        logger.error(f"Nie udało się pobrać strony {SOURCE_URL}. Błąd: {e}")
        return 0

    # Krok 2: Sparsuj HTML
    items = parse_badge_news_html(html_content)

    if not items:
        logger.info("Nie znaleziono żadnych elementów do przetworzenia.")
        return 0

    # Krok 3: Zapisz do bazy danych
    new_items_count = save_badge_news_items(items)

    logger.info(f"Zakończono proces scrapingu. Dodano {new_items_count} nowych wpisów.")
    return new_items_count
