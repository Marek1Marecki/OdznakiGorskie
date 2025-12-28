# odznaki/services/scoring_service.py
"""
Serwis do obliczania scoring (punktacji) dla POI i regionów.
Używa Django cache dla wydajności.
"""

import logging
import time
from collections import defaultdict
from datetime import date

from django.db.models import Q, prefetch_related_objects
from django.core.cache import cache
from django.conf import settings

from odznaki.models import Badge, PointOfInterest, Visit, BadgeRequirement

logger = logging.getLogger(__name__)

# Czas życia cache (5 minut)
SCORING_CACHE_TIMEOUT = getattr(settings, 'SCORING_CACHE_TIMEOUT', 300)


# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

def get_scoring_data_cached():
    """
    Pobiera dane scoring z Django cache.

    Cache flow:
    1. Sprawdź czy dane są w cache
    2. Jeśli TAK → zwróć z cache (szybko)
    3. Jeśli NIE → oblicz, zapisz do cache, zwróć

    TTL: 5 minut (lub SCORING_CACHE_TIMEOUT z settings)
    Invalidacja: Automatyczna przez signals po zmianie Visit/Badge
    """
    cache_key = 'scoring_data_v1'
    data = cache.get(cache_key)

    if data is None:
        logger.info("Scoring cache MISS - obliczam dane...")

        today = date.today()

        # Pobierz visits
        visits_by_poi = defaultdict(list)
        for visit in Visit.objects.values('point_of_interest_id', 'visit_date'):
            visits_by_poi[visit['point_of_interest_id']].append(visit['visit_date'])

        # Pobierz active badges
        active_badges = list(Badge.objects.filter(
            is_fully_achieved=False,
        ).filter(Q(start_date__lte=today) | Q(start_date__isnull=True))
                             .filter(Q(end_date__gte=today) | Q(end_date__isnull=True)))

        data = {
            'visits_by_poi': dict(visits_by_poi),
            'active_badges': active_badges,
        }

        cache.set(cache_key, data, timeout=SCORING_CACHE_TIMEOUT)
        logger.info(f"Scoring cache SET (TTL: {SCORING_CACHE_TIMEOUT}s)")
    else:
        logger.debug("Scoring cache HIT")

    return data


def invalidate_scoring_cache():
    """
    Ręczne usunięcie WSZYSTKICH cache scoring.
    W praktyce signals robią to automatycznie.
    """
    cache.delete('scoring_data_v1')
    cache.delete('dashboard_scores_full_v1')
    cache.delete('dashboard_scores_top_v1')
    logger.info("All scoring caches INVALIDATED (manual)")


# ============================================================================
# AGREGACJA
# ============================================================================

def _aggregate_parent_scores_from_base(base_scores_list):
    """
    Agreguje punkty dzieci do rodziców na podstawie już policzonej listy bazowej.
    Nie wykonuje żadnych zapytań ani ponownych obliczeń bazowych.
    """
    if not base_scores_list:
        return []

    scores_dict = {item['poi'].id: item for item in base_scores_list}
    children = [item['poi'] for item in base_scores_list if item['poi'].parent is not None]

    for child in children:
        if child.id in scores_dict and child.parent_id in scores_dict:
            child_score_item = scores_dict[child.id]
            parent_score_item = scores_dict[child.parent_id]
            parent_score_item['score'] += child_score_item['score']
            if 'aggregated_from' not in parent_score_item:
                parent_score_item['aggregated_from'] = []
            parent_score_item['aggregated_from'].append(child_score_item['poi'].name)

    final_results_list = list(scores_dict.values())
    return sorted(final_results_list, key=lambda item: item['score'], reverse=True)


def _aggregate_mesoregion_scores_from_base(base_scores_list):
    """
    Agreguje wyniki bazowe POI do poziomu mezoregionów na podstawie już policzonej listy bazowej.
    """
    mesoregion_scores = defaultdict(lambda: {'total_score': 0, 'pois': []})
    for item in base_scores_list:
        poi = item['poi']
        if poi.mesoregion:
            region_name = poi.mesoregion.name
            mesoregion_scores[region_name]['total_score'] += item['score']
            mesoregion_scores[region_name]['pois'].append(item)

    results_list = []
    for name, data in mesoregion_scores.items():
        sorted_pois_in_region = sorted(data['pois'], key=lambda x: x['score'], reverse=True)
        results_list.append({
            'mesoregion_name': name,
            'total_score': data['total_score'],
            'poi_count': len(data['pois']),
            'top_pois': sorted_pois_in_region[:5]
        })

    return sorted(results_list, key=lambda x: x['total_score'], reverse=True)


# ============================================================================
# OBLICZANIE SCORING
# ============================================================================

def calculate_poi_scores(active_badges, visits_by_poi):
    """
    Oblicza score dla POI na podstawie aktywnych odznak i wizyt.
    Używa danych z cache (przekazanych jako argumenty).
    """
    active_badge_ids = [b.id for b in active_badges]
    active_badges_map = {b.id: b for b in active_badges}

    requirements = list(
        BadgeRequirement.objects.filter(badge_id__in=active_badge_ids).values('badge_id', 'point_of_interest_id'))

    pois_by_badge = defaultdict(list)
    badges_by_poi = defaultdict(list)
    for req in requirements:
        pois_by_badge[req['badge_id']].append(req['point_of_interest_id'])
        badges_by_poi[req['point_of_interest_id']].append(req['badge_id'])

    remaining_counts = {}
    for badge_id, poi_ids in pois_by_badge.items():
        total_reqs = len(poi_ids)
        claimed_count = 0
        badge = active_badges_map[badge_id]
        for poi_id in poi_ids:
            for visit_date in visits_by_poi.get(poi_id, []):
                if (not badge.start_date or visit_date >= badge.start_date) and (
                    not badge.end_date or visit_date <= badge.end_date):
                    claimed_count += 1
                    break
        remaining_counts[badge_id] = total_reqs - claimed_count

    poi_scores = defaultdict(float)
    for poi_id, badge_ids in badges_by_poi.items():
        score = 0
        for badge_id in badge_ids:
            is_claimed = False
            badge = active_badges_map[badge_id]
            for visit_date in visits_by_poi.get(poi_id, []):
                if (not badge.start_date or visit_date >= badge.start_date) and (
                    not badge.end_date or visit_date <= badge.end_date):
                    is_claimed = True
                    break
            if not is_claimed:
                rem_count = remaining_counts.get(badge_id, 0)
                if rem_count > 0:
                    score += 100 / rem_count
        if score > 0:
            poi_scores[poi_id] = score

    if not poi_scores:
        return []

    scored_pois = PointOfInterest.objects.filter(id__in=poi_scores.keys())
    scored_pois_map = {p.id: p for p in scored_pois}

    results_list = []
    for poi_id, score in poi_scores.items():
        poi_obj = scored_pois_map.get(poi_id)
        if poi_obj:
            results_list.append({'poi': poi_obj, 'score': score, 'badges': []})

    return sorted(results_list, key=lambda item: item['score'], reverse=True)


def calculate_all_dashboard_scores(get_full_lists=False):
    """
    Oblicza rankingi dla dashboardu z FULL CACHE.

    OPTYMALIZACJA v3.0:
    - Nie zwraca base_poi_scores dla dashboard (2260 POI!)
    - Dashboard dostaje tylko top 10/5 (co rzeczywiście używa)
    - Oszczędność: 900ms → 50ms serializacji

    Performance:
        - Cold start: ~1.6s (oblicza wszystko)
        - Warm cache: ~0.05s (tylko top 10/5) - 32x szybciej!
    """
    # Klucze cache dla wyników
    cache_key_full = 'dashboard_scores_full_v1'
    cache_key_top = 'dashboard_scores_top_v1'

    # Wybierz odpowiedni klucz cache
    cache_key = cache_key_full if get_full_lists else cache_key_top

    # Sprawdź czy WYNIKI są w cache
    cached_results = cache.get(cache_key)

    if cached_results is not None:
        logger.debug(f"Dashboard scores cache HIT ({cache_key})")
        return cached_results

    # Cache miss - oblicz od zera
    logger.info(f"Dashboard scores cache MISS - obliczam...")

    # Pobierz dane bazowe z cache
    data = get_scoring_data_cached()
    visits_by_poi = data['visits_by_poi']
    active_badges = data['active_badges']

    # Oblicz bazowe score dla POI
    base_list = calculate_poi_scores(
        active_badges=active_badges,
        visits_by_poi=visits_by_poi
    )

    # Prefetch related objects
    if base_list:
        poi_objects_from_list = [item['poi'] for item in base_list]
        prefetch_related_objects(poi_objects_from_list, 'mesoregion', 'parent')

    # Agreguj wyniki
    full_poi_ranking = _aggregate_parent_scores_from_base(base_list)
    full_region_ranking = _aggregate_mesoregion_scores_from_base(base_list)

    # ========================================================================
    # ZMIANA: Różne dane dla full vs top
    # ========================================================================
    if get_full_lists:
        # Dla full: zwróć wszystko (używane przez get_score_for_single_poi)
        results = {
            'poi_ranking': full_poi_ranking,
            'region_ranking': full_region_ranking,
        }
    else:
        # Dla dashboard: TYLKO top 10/5 (bez base_poi_scores!)
        results = {
            'top_pois': full_poi_ranking[:10],
            'top_regions': full_region_ranking[:5],
            # ❌ USUNIĘTO: 'base_poi_scores': base_list,  # 2260 POI!
        }

    # Zapisz wyniki do cache
    cache.set(cache_key, results, timeout=SCORING_CACHE_TIMEOUT)
    logger.info(f"Dashboard scores cache SET ({cache_key}, TTL: {SCORING_CACHE_TIMEOUT}s)")

    return results


def calculate_scores_for_queryset(poi_queryset):
    """
    Oblicza score dla konkretnego querysetu POI.
    Używa cache dla danych bazowych.
    """
    logger.info("Uruchamiam calculate_scores_for_queryset...")
    start_time = time.time()

    if isinstance(poi_queryset, list):
        poi_ids = [poi.id for poi in poi_queryset]
    else:
        poi_ids = list(poi_queryset.values_list('id', flat=True))

    if not poi_ids:
        return {}

    # Pobierz dane z cache
    data = get_scoring_data_cached()
    active_badges = data['active_badges']
    all_visits_data = data['visits_by_poi']

    if not active_badges:
        return {}

    active_badge_ids = [b.id for b in active_badges]
    active_badges_map = {b.id: b for b in active_badges}

    # Pobierz wymagania
    requirements = list(BadgeRequirement.objects.filter(
        badge_id__in=active_badge_ids
    ).values('badge_id', 'point_of_interest_id'))

    # Zbuduj mapy
    pois_by_badge = defaultdict(list)
    badges_by_poi = defaultdict(list)
    poi_id_set = set(poi_ids)

    for req in requirements:
        pois_by_badge[req['badge_id']].append(req['point_of_interest_id'])
        if req['point_of_interest_id'] in poi_id_set:
            badges_by_poi[req['point_of_interest_id']].append(req['badge_id'])

    # Oblicz claimed pairs
    claimed_poi_badge_pairs = set()
    for badge_id, badge in active_badges_map.items():
        for poi_id_in_badge in pois_by_badge.get(badge_id, []):
            for visit_date in all_visits_data.get(poi_id_in_badge, []):
                if (not badge.start_date or visit_date >= badge.start_date) and \
                    (not badge.end_date or visit_date <= badge.end_date):
                    claimed_poi_badge_pairs.add((poi_id_in_badge, badge_id))
                    break

    # Oblicz remaining counts
    claimed_counts_by_badge = defaultdict(int)
    for _, badge_id in claimed_poi_badge_pairs:
        claimed_counts_by_badge[badge_id] += 1

    remaining_counts = {}
    for badge_id, required_poi_ids in pois_by_badge.items():
        total_reqs = len(required_poi_ids)
        claimed_count = claimed_counts_by_badge.get(badge_id, 0)
        remaining_counts[badge_id] = total_reqs - claimed_count

    # Oblicz score
    poi_scores = {}
    for poi_id in poi_id_set:
        score = 0
        for badge_id in badges_by_poi.get(poi_id, []):
            if (poi_id, badge_id) not in claimed_poi_badge_pairs:
                rem_count = remaining_counts.get(badge_id, 0)
                if rem_count > 0:
                    score += 100 / rem_count
        if score > 0:
            poi_scores[poi_id] = score

    elapsed = time.time() - start_time
    logger.info(f"calculate_scores_for_queryset: {len(poi_scores)} POI, {elapsed:.2f}s")

    return poi_scores


def get_score_for_single_poi(poi: PointOfInterest) -> float:
    """
    Oblicza PEŁNY, ZAGREGOWANY score dla jednego POI.
    Używa cache przez calculate_all_dashboard_scores().
    """
    cache_key = 'full_poi_ranking_for_details'
    full_ranking = cache.get(cache_key)

    if full_ranking is None:
        all_rankings = calculate_all_dashboard_scores(get_full_lists=True)
        full_ranking = all_rankings.get('poi_ranking', [])
        cache.set(cache_key, full_ranking, 300)

    for item in full_ranking:
        if item['poi'].id == poi.id:
            return item['score']

    return 0.0