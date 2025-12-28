# odznaki/apps.py

import logging
from django.apps import AppConfig
from django.core.cache import cache
from datetime import date
import threading
import os  # Potrzebne do sprawdzenia zmiennej środowiskowej

logger = logging.getLogger(__name__)

# Stała definiująca klucz w cache'u i czas życia (w sekundach)
# 86400 sekund = 24 godziny
CACHE_KEY = 'last_scrape_run_date'
CACHE_TIMEOUT = 86400


def run_scraping_task():
    """Funkcja opakowująca logikę scrapingu."""
    try:
        # Import serwisu wewnątrz funkcji, aby uniknąć problemów z cyklicznymi importami przy starcie
        from .services.scraping_service import scrape_badge_news

        logger.info("Uruchamianie zadania scrapingu w osobnym wątku...")
        scrape_badge_news()

        # Po udanym scrapingu, zapisujemy dzisiejszą datę do cache'u
        cache.set(CACHE_KEY, date.today().isoformat(), CACHE_TIMEOUT)
        logger.info("Zapisano datę ostatniego scrapingu w cache'u.")
    except Exception as e:
        logger.error(f"Wystąpił krytyczny błąd podczas uruchamiania zadania scrapingu: {e}", exc_info=True)


class OdznakiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "odznaki"

    def ready(self):
        """
        Metoda wywoływana, gdy aplikacja jest w pełni załadowana.
        To jest JEDYNE bezpieczne miejsce do importowania sygnałów.
        """
        # --- REJESTRACJA SYGNAŁÓW (POPRAWNA WERSJA) ---
        # Importujemy moduł sygnałów TUTAJ, wewnątrz `ready()`.
        # To gwarantuje, że modele są już w pełni załadowane.

        import odznaki.signals

        # --- Logika automatycznego scrapingu (pozostaje bez zmian) ---
        if os.environ.get('RUN_MAIN') != 'true':
            return

        last_run_str = cache.get(CACHE_KEY)
        today_str = date.today().isoformat()

        if last_run_str == today_str:
            logger.info("Scraping był już dzisiaj uruchomiony. Pomijam.")
            return

        logger.info("Planowanie jednorazowego uruchomienia zadania scrapingu...")
        scraping_thread = threading.Timer(5.0, run_scraping_task)
        scraping_thread.daemon = True
        scraping_thread.start()