from django.core.management.base import BaseCommand
from odznaki.models import MesoRegion, PointOfInterest
from django.contrib.gis.geos import Point
from django.db.models import Q

class Command(BaseCommand):
    help = 'Check POI assignments for a mesoregion'

    def handle(self, *args, **options):
        # Find the mesoregion
        try:
            mesoregion = MesoRegion.objects.get(name="Slezské Beskydy")
            self.stdout.write(self.style.SUCCESS(f'Found mesoregion: {mesoregion.name} (ID: {mesoregion.id})'))
        except MesoRegion.DoesNotExist:
            self.stdout.write(self.style.ERROR('Mesoregion "Slezské Beskydy" not found'))
            return
        except MesoRegion.MultipleObjectsReturned:
            self.stdout.write(self.style.ERROR('Multiple mesoregions with name "Slezské Beskydy" found'))
            return

        # 1. Get POIs directly assigned to the mesoregion
        direct_pois = mesoregion.points_of_interest.all()
        self.stdout.write(f'\n1. Directly assigned POIs: {direct_pois.count()}')
        for poi in direct_pois:
            self.stdout.write(f'   - {poi.name} (ID: {poi.id})')

        # 2. Get POIs that intersect with the mesoregion's shape
        if hasattr(mesoregion, 'shape') and mesoregion.shape:
            spatial_pois = PointOfInterest.objects.filter(location__within=mesoregion.shape)
            self.stdout.write(f'\n2. POIs within mesoregion shape: {spatial_pois.count()}')
            for poi in spatial_pois:
                self.stdout.write(f'   - {poi.name} (ID: {poi.id})')
            
            # 3. Find discrepancies
            direct_ids = set(direct_pois.values_list('id', flat=True))
            spatial_ids = set(spatial_pois.values_list('id', flat=True))
            
            in_spatial_not_direct = spatial_pois.exclude(id__in=direct_ids)
            if in_spatial_not_direct.exists():
                self.stdout.write('\nPOIs in shape but not directly assigned to mesoregion:')
                for poi in in_spatial_not_direct:
                    self.stdout.write(f'   - {poi.name} (ID: {poi.id}) - Current mesoregion: {poi.mesoregion}')
            
            in_direct_not_spatial = direct_pois.exclude(id__in=spatial_ids)
            if in_direct_not_spatial.exists():
                self.stdout.write('\nPOIs directly assigned but not within shape:')
                for poi in in_direct_not_spatial:
                    self.stdout.write(f'   - {poi.name} (ID: {poi.id}) - Location: {poi.location}')
        else:
            self.stdout.write('\nMesoregion has no shape defined for spatial query')
