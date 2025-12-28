# odznaki/management/commands/cache_benchmark.py
"""
Benchmark scoring z/bez cache.
Użycie: python manage.py cache_benchmark
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from odznaki.services.scoring_service import calculate_all_dashboard_scores
import time


class Command(BaseCommand):
    help = 'Benchmark scoring z/bez cache'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.HTTP_INFO(" CACHE BENCHMARK "))
        self.stdout.write("=" * 60)

        # ====================================================================
        # Test 1: Cold start (bez cache)
        # ====================================================================
        self.stdout.write("\n🧊 Test 1: COLD START (bez cache)")

        # Wyczyść WSZYSTKIE cache
        cache.delete('scoring_data_v1')
        cache.delete('dashboard_scores_full_v1')
        cache.delete('dashboard_scores_top_v1')
        cache.delete('full_poi_ranking_for_details')

        start = time.time()
        calculate_all_dashboard_scores(get_full_lists=False)
        cold_time = time.time() - start

        self.stdout.write(f"   Czas: {cold_time:.3f}s")

        # ====================================================================
        # Test 2: Warm cache (wszystkie cache aktywne)
        # ====================================================================
        self.stdout.write("\n🔥 Test 2: WARM CACHE (z cache)")

        # NIE czyścimy cache - sprawdzamy hit

        # Wielokrotne wywołania aby zmierzyć prawdziwy cache hit
        times = []
        for i in range(5):
            start = time.time()
            calculate_all_dashboard_scores(get_full_lists=False)
            elapsed = time.time() - start
            times.append(elapsed)

        # Użyj median jako najbardziej wiarygodnej wartości
        times.sort()
        warm_time = times[2]  # median z 5 prób

        self.stdout.write(f"   Czas (median z 5 prób): {warm_time:.3f}s")
        self.stdout.write(f"   Min: {min(times):.3f}s, Max: {max(times):.3f}s")

        # ====================================================================
        # Test 3: Sprawdź status cache
        # ====================================================================
        self.stdout.write("\n🔍 Test 3: STATUS CACHE")

        cache_keys = [
            'scoring_data_v1',
            'dashboard_scores_top_v1',
            'dashboard_scores_full_v1',
        ]

        active_count = 0
        for key in cache_keys:
            status = "✅ HIT" if cache.get(key) else "❌ MISS"
            self.stdout.write(f"   {key}: {status}")
            if cache.get(key):
                active_count += 1

        self.stdout.write(f"\n   Cache active: {active_count}/{len(cache_keys)}")

        # ====================================================================
        # Wyniki
        # ====================================================================
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📊 WYNIKI:")
        self.stdout.write(f"   Cold start:  {cold_time:.3f}s")
        self.stdout.write(f"   Warm cache:  {warm_time:.3f}s")

        if warm_time > 0:
            speedup = cold_time / warm_time
            self.stdout.write(
                self.style.SUCCESS(
                    f"   Przyspieszenie: {speedup:.1f}x"
                )
            )

            # Ocena wyników
            if speedup > 100:
                self.stdout.write(
                    self.style.SUCCESS(
                        "\n🎉 ŚWIETNIE! Cache działa znakomicie! (>100x)"
                    )
                )
            elif speedup > 10:
                self.stdout.write(
                    self.style.SUCCESS(
                        "\n🎉 Świetnie! Cache znacząco przyspiesza! (>10x)"
                    )
                )
            elif speedup > 5:
                self.stdout.write(
                    self.style.WARNING(
                        "\n👍 Dobrze, cache działa poprawnie. (>5x)"
                    )
                )
            elif speedup > 2:
                self.stdout.write(
                    self.style.WARNING(
                        "\n⚠️  Cache działa, ale przyspieszenie mogłoby być lepsze."
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        "\n❌ Cache nie przynosi znaczącej poprawy!"
                    )
                )

                if active_count < len(cache_keys):
                    self.stdout.write(
                        f"\n💡 Tylko {active_count}/{len(cache_keys)} cache aktywnych. "
                        "To może być przyczyną."
                    )
        else:
            self.stdout.write(
                self.style.ERROR("   Błąd: warm_time = 0")
            )

        # ====================================================================
        # Dodatkowa diagnostyka
        # ====================================================================
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("🔧 DIAGNOSTYKA:")

        # Sprawdź czy funkcja używa cache
        if active_count == len(cache_keys) and speedup < 5:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  Cache jest aktywny ale przyspieszenie małe."
                )
            )
            self.stdout.write("   Możliwe przyczyny:")
            self.stdout.write("   1. Mała baza danych (mało Visit/Badge)")
            self.stdout.write("   2. Szybki komputer (obliczenia są już szybkie)")
            self.stdout.write("   3. Inne bottlenecki (IO, rendering)")
            self.stdout.write(
                "\n   💡 W produkcji z większą bazą przyspieszenie będzie większe."
            )
        elif active_count < len(cache_keys):
            self.stdout.write(
                self.style.ERROR(
                    f"\n❌ Nie wszystkie cache są aktywne ({active_count}/{len(cache_keys)})"
                )
            )
            self.stdout.write("   Sprawdź logi czy są błędy podczas cache.set()")
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "\n✅ Cache działa prawidłowo!"
                )
            )

        self.stdout.write("=" * 60)