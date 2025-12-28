# ============================================================================
# odznaki/management/commands/cache_clear.py
# ============================================================================
"""
Czyści cache scoring.
Użycie: python manage.py cache_clear
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = 'Czyści cache scoring (force refresh)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Wyczyść WSZYSTKIE cache (nie tylko scoring)',
        )

    def handle(self, *args, **options):
        if options['all']:
            # Wyczyść cały cache
            cache.clear()
            self.stdout.write(
                self.style.SUCCESS('✅ Wyczyszczono CAŁY cache Django')
            )
        else:
            # Wyczyść tylko scoring cache
            cache_key = 'scoring_data_v1'
            cache.delete(cache_key)
            self.stdout.write(
                self.style.SUCCESS(f'✅ Wyczyszczono cache: {cache_key}')
            )

        self.stdout.write(
            "\n💡 Następny request do dashboard utworzy nowy cache."
        )
