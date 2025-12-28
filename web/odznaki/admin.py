# odznaki/admin.py

from django.contrib import admin
from django.utils.safestring import mark_safe
from leaflet.admin import LeafletGeoAdmin

from .models import (
    Country, Voivodeship, Province, SubProvince, MacroRegion, MesoRegion,
    Organizer, Booklet, PointOfInterest, PointOfInterestPhoto,
    Badge, BadgeLevel, BadgeRequirement, Visit, Trip, TripSegment,
    BadgeNewsItem,
)

from .services import visit_service
from .services import trip_service

# --- KLASY INLINE ---

class PointOfInterestPhotoInline(admin.TabularInline):
    model = PointOfInterestPhoto
    extra = 0
    fields = ('picture', 'description', 'photo_date')
    readonly_fields = ('created_at', 'updated_at')


class BadgeLevelInline(admin.TabularInline):
    model = BadgeLevel
    extra = 0
    ordering = ('order',)
    readonly_fields = ('created_at', 'updated_at')


class BadgeRequirementInline(admin.TabularInline):
    model = BadgeRequirement
    extra = 0
    autocomplete_fields = ['point_of_interest']


class TripSegmentInline(admin.TabularInline):
    model = TripSegment
    extra = 0
    ordering = ('sequence',)

    # Wyświetlamy teraz wszystkie nowe, indywidualne pola do stylizacji
    fields = (
        'sequence',
        'start_point_name',
        'end_point_name',
        'gpx_file',
        ('color', 'weight', 'dash_array'), # Grupujemy style w jednym wierszu
        'map_preview',
    )
    readonly_fields = ('gpx_path', 'map_preview', 'created_at', 'updated_at')

    def map_preview(self, obj):
        mock_request = None
        if obj.pk and obj.gpx_path:
            from odznaki.utils.map_utils.api import create_segment_preview_map_with_folium

            # Teraz dostajemy obiekt mapy
            folium_map = create_segment_preview_map_with_folium(obj, mock_request)

            if folium_map:
                # Ustawiamy wysokość i renderujemy HTML
                folium_map.get_root().height = "200px"
                return mark_safe(folium_map._repr_html_())
        return "Zapisz segment z plikiem GPX, aby zobaczyć podgląd mapy."


# --- REJESTRACJA MODELI ---

# --- Modele geograficzne (bez zmian) ---
@admin.register(Country)
class CountryAdmin(LeafletGeoAdmin):
    list_display = ('name', 'code', 'order') # <-- ZMIANA
    list_editable = ('order',) # <-- NOWA LINIA
    search_fields = ('name', 'code')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        # Dodajemy 'order' do fieldsetu
        ('Informacje Główne', {'fields': ('name', 'translation', 'code', 'order', 'link')}),
        ('Dane Geograficzne', {'fields': ('shape',)}),
        ('Znaczniki Czasu', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(Voivodeship)
class VoivodeshipAdmin(LeafletGeoAdmin):
    list_display = ('name', 'country', 'code')
    search_fields = ('name', 'code')
    list_filter = ('country',)
    autocomplete_fields = ('country',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('country',)}),
        ('Informacje Główne', {'fields': ('name', 'translation', 'code', 'link')}),
        ('Dane Geograficzne', {'fields': ('shape',)}),
        ('Znaczniki Czasu', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(Province)
class ProvinceAdmin(LeafletGeoAdmin):
    list_display = ('name', 'country', 'code')
    search_fields = ('name', 'code')
    list_filter = ('country',)
    autocomplete_fields = ('country',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('country',)}),
        ('Informacje Główne', {'fields': ('name', 'translation', 'code', 'link')}),
        ('Dane Geograficzne', {'fields': ('shape',)}),
        ('Znaczniki Czasu', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(SubProvince)
class SubProvinceAdmin(LeafletGeoAdmin):
    list_display = ('name', 'province', 'code')
    search_fields = ('name', 'code')
    list_filter = ('province',)
    autocomplete_fields = ('province',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('province',)}),
        ('Informacje Główne', {'fields': ('name', 'translation', 'code', 'link')}),
        ('Dane Geograficzne', {'fields': ('shape',)}),
        ('Znaczniki Czasu', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(MacroRegion)
class MacroRegionAdmin(LeafletGeoAdmin):
    list_display = ('name', 'subprovince', 'code')
    search_fields = ('name', 'code')
    list_filter = ('subprovince',)
    autocomplete_fields = ('subprovince',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('subprovince',)}),
        ('Informacje Główne', {'fields': ('name', 'translation', 'code', 'link')}),
        ('Dane Geograficzne', {'fields': ('shape',)}),
        ('Znaczniki Czasu', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(MesoRegion)
class MesoRegionAdmin(LeafletGeoAdmin):
    list_display = ('name', 'macroregion', 'code')
    search_fields = ('name', 'code')
    list_filter = ('macroregion',)
    autocomplete_fields = ('macroregion',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('macroregion',)}),
        ('Informacje Główne', {'fields': ('name', 'translation', 'code', 'link')}),
        ('Dane Geograficzne', {'fields': ('shape',)}),
        ('Znaczniki Czasu', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


# --- Modele główne ---

@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ('name', 'link', 'email', 'booklet_required', 'decoration_required')
    search_fields = ('name', 'secondary_name')
    list_filter = ('booklet_required', 'decoration_required')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Informacje Główne', {'fields': ('name', 'secondary_name', 'link', 'email', 'address')}),
        ('Ustawienia i Regulaminy',
         {'fields': ('booklet_required', ('decoration_required', 'decoration_scan'), 'statute', 'statute_date')}),
        ('Informacje o Członkostwie', {'fields': ('date_of_accession',)}),
        ('Znaczniki Czasu', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

@admin.register(Booklet)
class BookletAdmin(admin.ModelAdmin):
    list_display = ('name', 'booklet_type', 'organizer', 'is_possessed', 'valid_from', 'valid_to')
    search_fields = ('name', 'club_number')
    list_filter = ('booklet_type', 'is_possessed', 'organizer')
    autocomplete_fields = ('organizer',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Informacje Podstawowe',
         {'fields': ('name', 'booklet_type', 'organizer', ('sequence_number', 'club_number'))}),
        ('Status Posiadania', {'fields': (('is_required', 'is_possessed'),)}),
        ('Okres Ważności', {'fields': (('valid_from', 'valid_to'),)}),
        ('Pliki Cyfrowe', {'fields': ('image', ('scan', 'scan_date'))}),
        ('Znaczniki Czasu', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(PointOfInterest)
class PointOfInterestAdmin(LeafletGeoAdmin):
    list_display = ('name', 'category', 'height', 'mesoregion', 'voivodeship',
                    'is_active')  # Dodajemy 'voivodeship' do listy
    search_fields = ('name', 'secondary_name', 'code')
    list_filter = ('category', 'is_active', 'mesoregion', 'voivodeship')  # Dodajemy 'voivodeship' do filtrów

    # Dodajemy 'voivodeship' do pól autouzupełniania
    autocomplete_fields = ('mesoregion', 'parent', 'voivodeship', 'country')

    inlines = [PointOfInterestPhotoInline]
    readonly_fields = ('created_at', 'updated_at')

    # Aktualizujemy fieldsets, aby zawierały nowe pole
    fieldsets = (
        ('Informacje Podstawowe', {
            'fields': (('name', 'secondary_name'), 'category', 'parent', ('height', 'code'), 'is_active')
        }),
        ('Lokalizacja', {
            # Dodajemy pole 'voivodeship' obok mezoregionu
            'fields': ('mesoregion', 'voivodeship', 'country', 'location')
        }),
        ('Dodatkowe Informacje', {
            'fields': ('link',),
        }),
        ('Znaczniki Czasu', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'organizer', 'required_poi_count', 'total_poi_count', 'is_fully_achieved')
    search_fields = ('name', 'organizer__name')
    list_filter = ('is_fully_achieved', 'organizer')
    autocomplete_fields = ('organizer', 'booklet')
    inlines = [BadgeLevelInline, BadgeRequirementInline]
    readonly_fields = ('is_fully_achieved', 'created_at', 'updated_at')
    fieldsets = (
        ('Informacje Główne', {'fields': ('name', 'organizer', 'booklet')}),
        ('Wymagania', {'fields': (('required_poi_count', 'total_poi_count'),)}),
        ('Regulamin i Daty', {
            'fields': ('statute', ('statute_date', 'establishment_date'), ('start_date', 'end_date'), 'statute_link',
                       'link')}),
        ('Status (Automatyczny)', {'fields': ('is_fully_achieved',)}),
        ('Znaczniki Czasu', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('point_of_interest', 'visit_date')
    search_fields = ('point_of_interest__name', 'description')
    list_filter = ('visit_date',)
    autocomplete_fields = ('point_of_interest',)
    date_hierarchy = 'visit_date'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('point_of_interest', 'visit_date')}),
        ('Szczegóły Potwierdzenia', {'fields': ('description', ('got_booklet_number', 'entry_on_page'))}),
        ('Znaczniki Czasu', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    # Nadpisujemy domyślną metodę zapisu
    def save_model(self, request, obj, form, change):
        """
        Przy zapisie z panelu admina, użyj naszego serwisu,
        aby zapewnić walidację i aktualizację powiązanych odznak.
        """
        visit_service.create_or_update_visit(obj)

    # Nadpisujemy domyślną metodę usuwania
    def delete_model(self, request, obj):
        """
        Przy usuwaniu z panelu admina, użyj naszego serwisu.
        """
        visit_service.delete_visit(obj)

    def delete_queryset(self, request, queryset):
        """
        Obsługuje usuwanie wielu obiektów naraz (akcja w adminie).
        """
        for obj in queryset:
            visit_service.delete_visit(obj)


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    # Ulepszamy list_display, aby od razu pokazywać kluczowe statystyki
    list_display = (
        '__str__',
        'date',
        'total_distance_km',
        'total_elevation_gain_m',
        'got_points',
        'total_gpx_paths'
    )
    inlines = [TripSegmentInline]
    change_form_template = 'admin/odznaki/trip/change_form.html'
    date_hierarchy = 'date'
    search_fields = ('start_point_name', 'end_point_name', 'description')

    # --- GŁÓWNA ZMIANA JEST TUTAJ ---
    # Dodajemy nasze pola obliczeniowe do listy pól tylko do odczytu.
    # Dodajemy też standardowe 'created_at' i 'updated_at'.
    readonly_fields = (
        'created_at',
        'updated_at',
        'total_distance_km',
        'total_elevation_gain_m',
        'got_points',
        'everest_diff_m'
    )

    # Aktualizujemy fieldsets, aby pokazywać pola tylko do odczytu
    # w osobnej, zwiniętej sekcji.
    fieldsets = (
        (None, {
            'fields': ('date', ('start_point_name', 'end_point_name'))
        }),
        ('Szczegóły Wycieczki', {
            'fields': ('description',)
        }),
        # --- NOWA SEKCJA W FIELDSETS ---
        ('Obliczone Statystyki (Tylko do odczytu)', {
            'fields': (
                ('total_distance_km', 'total_elevation_gain_m'),
                ('got_points', 'everest_diff_m')
            ),
            'classes': ('collapse',) # Domyślnie zwinięta, żeby nie zaśmiecać
        }),
        # --- KONIEC NOWEJ SEKCJI ---
        ('Znaczniki Czasu', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # Nasza metoda do generowania mapy
    # Nasza metoda do generowania mapy
    def get_trip_map(self, obj, request): # <-- Dodajemy `request`
        """
        Renderuje mapę podglądową dla wycieczki w panelu admina.
        """
        if obj.pk:
            # Użycie NOWEJ, dedykowanej funkcji do podglądu
            from odznaki.utils.map_utils.api import create_trip_preview_map_for_admin
            folium_map = create_trip_preview_map_for_admin(obj, request)
            if folium_map:
                folium_map.get_root().height = "500px"
                return mark_safe(folium_map._repr_html_())
        return "Zapisz wycieczkę i dodaj segmenty GPX, aby zobaczyć mapę."

    # Nadpisujemy widok, aby przekazać 'request' do naszej metody
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        trip_object = self.get_object(request, object_id)
        if trip_object:
            # Przekazujemy teraz `request` do `get_trip_map`
            extra_context['trip_map_html'] = self.get_trip_map(trip_object, request)
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context,
        )

    def save_related(self, request, form, formsets, change):
        # Standardowy zapis modelu i jego inlines
        super().save_related(request, form, formsets, change)
        # Po zapisaniu wszystkiego, uruchamiamy przeliczenie dla
        # obiektu Trip, który właśnie edytowaliśmy.
        trip_service.recalculate_trip_stats(form.instance)


@admin.register(TripSegment)
class TripSegmentAdmin(LeafletGeoAdmin):
    list_display = ('__str__', 'trip', 'sequence')
    list_filter = ('trip',)
    search_fields = ('start_point_name', 'end_point_name')

    # Używamy fieldsets dla lepszego układu
    fieldsets = (
        ('Informacje Podstawowe', {
            'fields': ('trip', 'sequence', 'start_point_name', 'end_point_name')
        }),
        ('Import Danych', {
            'fields': ('gpx_file',)
        }),
        ('Opcje Stylizacji', {
            'fields': (('color', 'weight', 'dash_array'),)
        }),
        ('Podgląd Mapy', {
            'fields': ('map_preview',)  # <-- NASZE WIRTUALNE POLE
        }),
        ('Dane Techniczne', {
            'fields': ('gpx_path', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('gpx_path', 'map_preview', 'created_at', 'updated_at')

    def map_preview(self, obj):
        mock_request = None
        if obj.pk and obj.gpx_path:
            from odznaki.utils.map_utils.api import create_segment_preview_map_with_folium

            # Teraz dostajemy obiekt mapy
            folium_map = create_segment_preview_map_with_folium(obj, mock_request)

            if folium_map:
                # Ustawiamy wysokość i renderujemy HTML
                folium_map.get_root().height = "500px"
                return mark_safe(folium_map._repr_html_())
        return "Zapisz segment z plikiem GPX, aby zobaczyć podgląd mapy."


@admin.register(BadgeNewsItem)
class BadgeNewsItemAdmin(admin.ModelAdmin):
    list_display = ('badge_name', 'change_type', 'change_date_str', 'is_dismissed', 'created_at')
    list_filter = ('change_type', 'is_dismissed')
    search_fields = ('badge_name',)
    list_editable = ('is_dismissed',)
    readonly_fields = ('created_at', 'updated_at')


# Rejestracja pozostałych modeli
admin.site.register(BadgeLevel)
admin.site.register(BadgeRequirement)
admin.site.register(PointOfInterestPhoto)

