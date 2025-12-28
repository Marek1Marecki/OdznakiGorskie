from django.db import models
from .base import LocationModel
from odznaki.managers import (
    CountryManager, VoivodeshipManager, ProvinceManager,
    SubProvinceManager, MacroRegionManager, MesoRegionManager
)


# === Abstrakcyjna klasa bazowa dla modeli hierarchicznych ===

class HierarchicalLocationModel(LocationModel):
    """Abstrakcyjna klasa bazowa dla modeli geograficznych, które są częścią hierarchii.
    
    Atrybuty:
        Dziedziczy wszystkie atrybuty z LocationModel.
        
    Uwagi:
        Klasa jest abstrakcyjna i służy jako klasa bazowa dla modeli geograficznych
        z hierarchią (np. kraj -> województwo -> powiat itp.).
        
    Metody:
        get_parent(): Abstrakcyjna metoda do zaimplementowania przez klasy potomne.
        get_hierarchy(): Zwraca pełną hierarchię obiektów.
        get_hierarchy_path(): Zwraca ścieżkę hierarchii jako string.
    """
    class Meta:
        abstract = True

    def get_parent(self):
        """Zwraca bezpośredniego rodzica w hierarchii.
        
        Returns:
            HierarchicalLocationModel: Obiekt rodzica w hierarchii.
            
        Raises:
            NotImplementedError: Jeśli metoda nie zostanie zaimplementowana w klasie potomnej.
            
        Uwagi:
            Metoda abstrakcyjna - musi być zaimplementowana w klasach potomnych.
        """
        raise NotImplementedError("Każdy model hierarchiczny musi implementować get_parent()")

    def get_hierarchy(self) -> list['HierarchicalLocationModel']:
        """Zwraca listę obiektów tworzących pełną hierarchię.
        
        Returns:
            list[HierarchicalLocationModel]: Lista obiektów od najwyższego poziomu (korzenia)
                do bieżącego obiektu (włącznie).
                
        Uwagi:
            Wykorzystuje funkcję pomocniczą get_location_hierarchy z modułu geo_helpers.
        """
        # IMPORT LOKALNY
        from odznaki.utils import geo_helpers
        return geo_helpers.get_location_hierarchy(self)

    def get_hierarchy_path(self, separator: str = ' > ') -> str:
        """Zwraca pełną ścieżkę hierarchii jako string.
        
        Args:
            separator (str, optional): Separator używany do łączenia nazw obiektów w ścieżce.
                Domyślnie ' > '.
                
        Returns:
            str: String reprezentujący pełną ścieżkę hierarchii, np. 'Polska > Małopolskie > Tatry'.
                
        Przykład:
            >>> country = Country(name='Polska')
            >>> voivodeship = Voivodeship(name='Małopolskie', country=country)
            >>> region = Region(name='Tatry', voivodeship=voivodeship)
            >>> region.get_hierarchy_path()
            'Polska > Małopolskie > Tatry'
        """
        # IMPORT LOKALNY
        from odznaki.utils import geo_helpers
        return geo_helpers.get_hierarchy_path(self, separator=separator)


# === Modele geograficzne ===

class Country(HierarchicalLocationModel):
    """Reprezentuje kraj w hierarchii geograficznej.
    
    Atrybuty:
        Dziedziczy wszystkie atrybuty z HierarchicalLocationModel.
        
    Uwagi:
        Kraj stanowi korzeń (root) hierarchii geograficznej.
        
    Metody:
        get_parent(): Zawsze zwraca None, ponieważ kraj nie ma rodzica.
    """
    objects = CountryManager()
    order = models.PositiveIntegerField(
        default=999,
        verbose_name="Kolejność",
        help_text="Im niższa liczba, tym wyżej na liście. Używane do sortowania.",
        db_index=True
    )

    class Meta:
        db_table = 'odznaki_country'
        verbose_name = 'Kraj'
        verbose_name_plural = 'Kraje'
        ordering = ['order']

    def get_parent(self):
        """Kraj nie ma rodzica, więc zwracamy None."""
        return None


class Voivodeship(HierarchicalLocationModel):
    """Reprezentuje województwo (jednostka administracyjna).
    
    Atrybuty:
        country (ForeignKey): Klucz obcy do modelu Country - kraj, do którego należy województwo.
        
    Uwagi:
        Każde województwo musi należeć do dokładnie jednego kraju.
        
    Metody:
        get_parent(): Zwraca kraj, do którego należy województwo.
    """
    objects = VoivodeshipManager()

    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name='voivodeships',
        verbose_name="Kraj",
        help_text="Kraj, w którym znajduje się województwo"
    )

    class Meta:
        db_table = 'odznaki_voivodeship'
        verbose_name = 'Województwo'
        verbose_name_plural = 'Województwa'
        ordering = ['country__name', 'name']
        constraints = [
            models.UniqueConstraint(fields=['country', 'code'], name='unique_voivodeship_code_per_country'),
            models.UniqueConstraint(fields=['country', 'name'], name='unique_voivodeship_name_per_country')
        ]

    def get_parent(self):
        """Rodzicem województwa jest kraj."""
        return self.country

    def __str__(self) -> str:
        return f"{self.name} ({self.country.name})"


class Province(HierarchicalLocationModel):
    """Reprezentuje region (np. górska grupa, park narodowy).
    
    Atrybuty:
        country (ForeignKey): Klucz obcy do modelu Country - kraj, do którego należy region.
        
    Uwagi:
        Każdy region musi należeć do dokładnie jednego kraju.
        
    Metody:
        get_parent(): Zwraca kraj, do którego należy region.
    """
    objects = ProvinceManager()

    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        related_name='provinces',
        verbose_name="Kraj",
        help_text="Kraj, w którym leży prowincja"
    )

    class Meta:
        db_table = 'odznaki_province'
        verbose_name = 'Prowincja'
        verbose_name_plural = 'Prowincje'
        ordering = ['country__name', 'name']
        constraints = [
            models.UniqueConstraint(fields=['country', 'code'], name='unique_province_code_per_country')
        ]

    def get_parent(self):
        """Rodzicem prowincji jest kraj."""
        return self.country

    def __str__(self) -> str:
        return f"{self.name} ({self.country.name})"


class SubProvince(HierarchicalLocationModel):
    """Reprezentuje podregion (np. pasmo górskie, część parku narodowego).
    
    Atrybuty:
        province (ForeignKey): Klucz obcy do modelu Province - region nadrzędny,
            do którego należy podregion.
        
    Uwagi:
        Każdy podregion musi należeć do dokładnie jednego regionu.
        
    Metody:
        get_parent(): Zwraca region, do którego należy podregion.
    """
    objects = SubProvinceManager()

    province = models.ForeignKey(
        Province,
        on_delete=models.PROTECT,
        related_name='subprovinces',
        verbose_name="Prowincja",
        help_text="Prowincja nadrzędna nad podprowincją"
    )

    class Meta:
        db_table = 'odznaki_subprovince'
        verbose_name = 'Podprowincja'
        verbose_name_plural = 'Podprowincje'
        ordering = ['province__name', 'name']
        constraints = [
            models.UniqueConstraint(fields=['province', 'code'], name='unique_subprovince_code_per_province')
        ]

    def get_parent(self):
        """Rodzicem podprowincji jest prowincja."""
        return self.province

    def __str__(self) -> str:
        return f"{self.name} ({self.province.name})"


class MacroRegion(HierarchicalLocationModel):
    """Reprezentuje makroregion (np. duży obszar górski).
    
    Atrybuty:
        subprovince (ForeignKey): Opcjonalny klucz obcy do modelu SubProvince - 
            podregion nadrzędny, do którego należy makroregion.
        
    Uwagi:
        Makroregion może, ale nie musi, należeć do podregionu (null=True).
        
    Metody:
        get_parent(): Zwraca podregion, do którego należy makroregion, lub None.
    """
    objects = MacroRegionManager()

    subprovince = models.ForeignKey(
        SubProvince,
        on_delete=models.PROTECT,
        related_name='macroregions',
        verbose_name="Podprowincja",
        help_text="Podprowincja nadrzędna nad makroregionem",
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'odznaki_macroregion'
        verbose_name = 'Makroregion'
        verbose_name_plural = 'Makroregiony'
        ordering = ['subprovince__name', 'name']
        constraints = [
            models.UniqueConstraint(fields=['subprovince', 'code'], name='unique_macroregion_code_per_subprovince')
        ]

    def get_parent(self):
        """Rodzicem makroregionu jest podprowincja."""
        return self.subprovince

    def __str__(self) -> str:
        return f"{self.name} ({self.subprovince.name})"


class MesoRegion(HierarchicalLocationModel):
    """Reprezentuje mezoregion fizycznogeograficzny.
    
    Atrybuty:
        macroregion (ForeignKey): Klucz obcy do modelu MacroRegion - 
            makroregion nadrzędny, do którego należy mezoregion.
            
    Uwagi:
        Każdy mezoregion musi należeć do dokładnie jednego makroregionu.
        
    Metody:
        get_parent(): Zwraca makroregion, do którego należy mezoregion.
    """
    objects = MesoRegionManager()

    macroregion = models.ForeignKey(
        MacroRegion,
        on_delete=models.PROTECT,
        related_name='mesoregions',
        verbose_name="Makroregion",
        help_text="Makroregion nadrzędny nad mezoregionem"
    )

    class Meta:
        db_table = 'odznaki_mesoregion'
        verbose_name = 'Mezoregion'
        verbose_name_plural = 'Mezoregiony'
        ordering = ['macroregion__name', 'name']
        constraints = [
            models.UniqueConstraint(fields=['macroregion', 'code'], name='unique_mesoregion_code_per_macroregion'),
            models.UniqueConstraint(fields=['macroregion', 'name'], name='unique_mesoregion_name_per_macroregion')
        ]

    def get_parent(self):
        """Zwraca makroregion, do którego należy mezoregion.
        
        Returns:
            MacroRegion: Obiekt makroregionu, do którego należy mezoregion.
        """
        return self.macroregion

    def __str__(self) -> str:
        """
        Zwraca czytelną reprezentację tekstową mezoregionu,
        delegując logikę formatowania do warstwy serwisowej.
        """
        # Import lokalny, aby uniknąć problemów z cyklicznymi zależnościami
        from odznaki.services.geography_service import get_mesoregion_display_name
        return get_mesoregion_display_name(self)
