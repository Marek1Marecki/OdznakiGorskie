# odznaki/management/commands/cache_status.py
"""
Wyświetla status cache scoring.
Użycie: python manage.py cache_status
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone


class Command(BaseCommand):
    help = 'Wyświetla status WSZYSTKICH cache scoring'

    def handle(self, *args, **options):
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.HTTP_INFO(" SCORING CACHE STATUS (v2.0) "))
        self.stdout.write("=" * 70)

        cache_keys = {
            'scoring_data_v1': 'Dane bazowe (visits + badges)',
            'dashboard_scores_top_v1': 'Wyniki dashboard (top 10/5)',
            'dashboard_scores_full_v1': 'Wyniki dashboard (full)',
            'full_poi_ranking_for_details': 'POI detail ranking',
        }

        active_count = 0

        for cache_key, description in cache_keys.items():
            self.stdout.write(f"\n📦 {description}")
            self.stdout.write(f"   Key: {cache_key}")

            data = cache.get(cache_key)

            if data is None:
                self.stdout.write(self.style.WARNING("   ❌ PUSTY"))
            else:
                self.stdout.write(self.style.SUCCESS("   ✅ AKTYWNY"))
                active_count += 1

                # Pokaż szczegóły
                if isinstance(data, dict):
                    # Statystyki dla scoring_data_v1
                    if 'visits_by_poi' in data:
                        visits_count = sum(len(dates) for dates in data['visits_by_poi'].values())
                        self.stdout.write(f"   📊 Wizyt: {visits_count}")
                        self.stdout.write(f"   📊 POI z wizytami: {len(data['visits_by_poi'])}")

                    if 'active_badges' in data:
                        self.stdout.write(f"   📊 Aktywnych odznak: {len(data['active_badges'])}")

                    # Statystyki dla dashboard_scores
                    if 'top_pois' in data:
                        self.stdout.write(f"   📊 Top POI: {len(data.get('top_pois', []))}")
                        self.stdout.write(f"   📊 Top regions: {len(data.get('top_regions', []))}")

                    if 'poi_ranking' in data:
                        self.stdout.write(f"   📊 Full POI ranking: {len(data.get('poi_ranking', []))}")

                # Dla list
                elif isinstance(data, list):
                    self.stdout.write(f"   📊 Items: {len(data)}")

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(f"\n📈 Podsumowanie: {active_count}/{len(cache_keys)} cache aktywnych")

        if active_count == 0:
            self.stdout.write(
                self.style.WARNING(
                    "\n💡 Cache pusty - odwiedź dashboard aby cache został utworzony"
                )
            )
        elif active_count == len(cache_keys):
            self.stdout.write(
                self.style.SUCCESS(
                    "\n🎉 Wszystkie cache aktywne - dashboard będzie błyskawiczny!"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  Tylko {active_count}/{len(cache_keys)} cache - "
                    "odwiedź dashboard aby uzupełnić"
                )
            )

        self.stdout.write("\n" + "=" * 70)