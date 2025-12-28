"""Niestandardowe klasy QuerySet i Manager dla modeli."""

from django.db import models
from django.db.models import Count, Max, Prefetch

# ===================================================
# MENEDŻERY I QUERYSETY DLA MODELI GEOGRAFICZNYCH
# ===================================================

class HierarchicalQuerySet(models.QuerySet):
    """
    Bazowy QuerySet dla modeli hierarchicznych, który zapewnia optymalizację
    zapytań poprzez automatyczne używanie select_related dla relacji w górę hierarchii.
    """
    pass


class CountryManager(models.Manager):
    """Menedżer dla modelu Country."""
    
    def get_queryset(self):
        return HierarchicalQuerySet(self.model, using=self._db)


class VoivodeshipManager(models.Manager):
    """Menedżer dla modelu Voivodeship z optymalizacją zapytań."""
    
    def get_queryset(self):
        return HierarchicalQuerySet(self.model, using=self._db).select_related('country')


class ProvinceManager(models.Manager):
    """Menedżer dla modelu Province z optymalizacją zapytań."""
    
    def get_queryset(self):
        return HierarchicalQuerySet(self.model, using=self._db).select_related('country')


class SubProvinceManager(models.Manager):
    """Menedżer dla modelu SubProvince z optymalizacją zapytań."""
    
    def get_queryset(self):
        return HierarchicalQuerySet(self.model, using=self._db).select_related(
            'province__country'
        )


class MacroRegionManager(models.Manager):
    """Menedżer dla modelu MacroRegion z optymalizacją zapytań."""
    
    def get_queryset(self):
        return HierarchicalQuerySet(self.model, using=self._db).select_related(
            'subprovince__province__country'
        )


class MesoRegionManager(models.Manager):
    """Menedżer dla modelu MesoRegion z optymalizacją zapytań."""
    
    def get_queryset(self):
        return HierarchicalQuerySet(self.model, using=self._db).select_related(
            'macroregion__subprovince__province__country'
        )


# ===================================================
# MENEDŻERY I QUERYSETY DLA MODELI APLIKACJI
# ===================================================

class PointOfInterestQuerySet(models.QuerySet):
    """Niestandardowy QuerySet dla modelu PointOfInterest."""
    
    def with_last_visited_date(self):
        """
        Dodaje do każdego obiektu PointOfInterest adnotację 'last_visited_date'
        zawierającą datę ostatniej wizyty.

        Wykorzystuje Subquery, aby uniknąć problemu N+1 zapytań.
        """
        from django.db.models import OuterRef, Subquery
        from odznaki.models.visit import Visit
        
        # Tworzymy podzapytanie, które dla każdego PointOfInterest (OuterRef('pk'))
        # znajdzie najnowszą datę wizyty.
        last_visit_subquery = Visit.objects.filter(
            point_of_interest=OuterRef('pk')
        ).order_by('-visit_date').values('visit_date')[:1]

        # Dodajemy to podzapytanie jako nowe, wirtualne pole 'last_visited_date'
        # do naszego głównego QuerySetu.
        return self.annotate(
            last_visited_date=Subquery(last_visit_subquery)
        )
    
    def with_full_geography(self):
        """
        Pobiera obiekty PointOfInterest wraz ze wszystkimi powiązanymi danymi
        geograficznymi w jednym zapytaniu.
        """
        return self.select_related(
            'mesoregion__macroregion__subprovince__province__country'
        )

    def with_visits(self):
        """Pobiera punkty POI wraz z powiązanymi wizytami, optymalizując zapytania.
        
        Returns:
            QuerySet: Kwerenda z dołączonymi wizytami w jednym zapytaniu.
        """
        return self.prefetch_related('visits')

    def with_visit_stats(self):
        """
        Dodaje annotacje z statystykami wizyt.
        Użyj zamiast property visit_stats!

        Przykład:
            pois = PointOfInterest.objects.with_visit_stats()
            for poi in pois:
                print(poi.visit_count)  # Bez dodatkowych queries!
        """
        return self.annotate(
            visit_count=Count('visits'),
            last_visited_date=Max('visits__visit_date')
        )

    def with_full_hierarchy(self):
        """Ładuje pełną hierarchię geograficzną - optymalizacja POI.save()."""
        return self.select_related(
            'mesoregion__macroregion__subprovince__province__country',
            'voivodeship',
            'country',
            'parent'
        )

    def with_visits_prefetched(self):
        """Prefetchuje wizyty - optymalizacja dla has_visits."""
        return self.prefetch_related('visits')

    def active_objects(self):
        """Zwraca tylko aktywne obiekty."""
        return self.filter(is_active=True)


class VisitQuerySet(models.QuerySet):
    """Niestandardowy QuerySet dla modelu Visit (dawniej Achievement)."""
    
    def recent(self, days=30):
        """Zwraca ostatnie wizyty z określonej liczby dni."""
        from django.utils import timezone
        from django.db.models.functions import Now
        
        return self.filter(
            visit_date__gte=timezone.now().date() - timezone.timedelta(days=days)
        )


class BadgeRequirementQuerySet(models.QuerySet):
    """Niestandardowy QuerySet dla modelu BadgeRequirement (dawniej Listofobjects)."""
    
    def get_obligatory_objects(self, badge):
        """Zwraca obowiązkowe obiekty dla danej odznaki."""
        return self.filter(badge=badge, obligatory=True)


class BadgeRequirementManager(models.Manager):
    """Menedżer dla modelu BadgeRequirement."""
    
    def get_queryset(self):
        return BadgeRequirementQuerySet(self.model, using=self._db)
    
    def get_obligatory_objects(self, badge):
        return self.get_queryset().get_obligatory_objects(badge)
