# ============================================================================
# odznaki/management/commands/cache_warm.py
# ============================================================================
"""
Wygrzewa cache (tworzy przed pierwszym requestem).
Użycie: python manage.py cache_warm
"""

from django.core.management.base import BaseCommand
from odznaki.services.scoring_service import get_scoring_data_cached
import time


class Command(BaseCommand):
    help = 'Wygrzewa cache scoring (cache warming)'

    def handle(self, *args, **options):
        self.stdout.write("🔥 Rozpoczynam cache warming...")

        start = time.time()

        try:
            data = get_scoring_data_cached()
            elapsed = time.time() - start

            visits_count = sum(
                len(dates) for dates in data['visits_by_poi'].values()
            )
            badges_count = len(data['active_badges'])

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Cache utworzony pomyślnie w {elapsed:.2f}s"
                )
            )
            self.stdout.write(f"   - Wizyt: {visits_count}")
            self.stdout.write(f"   - Aktywnych odznak: {badges_count}")
            self.stdout.write(
                "\n💡 Dashboard będzie teraz ładował się błyskawicznie!"
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\n❌ Błąd podczas cache warming: {e}")
            )
            raise
        