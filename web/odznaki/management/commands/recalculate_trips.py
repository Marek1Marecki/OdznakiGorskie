# odznaki/management/commands/recalculate_trips.py

from django.core.management.base import BaseCommand
from odznaki.models import Trip
from odznaki.services import trip_service

class Command(BaseCommand):
    help = 'Przelicza i zapisuje statystyki (dystans, GOT, etc.) dla wszystkich wycieczek w bazie.'

    def handle(self, *args, **options):
        self.stdout.write("Rozpoczynam przeliczanie statystyk dla wszystkich wycieczek...")
        
        all_trips = Trip.objects.prefetch_related('gpx_paths').all()
        
        for trip in all_trips:
            self.stdout.write(f"  -> Przetwarzam wycieczkę: {trip} (ID: {trip.id})")
            try:
                trip_service.recalculate_trip_stats(trip)
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  ! Błąd podczas przetwarzania wycieczki ID {trip.id}: {e}"))
                
        self.stdout.write(self.style.SUCCESS("Pomyślnie zakończono przeliczanie statystyk."))