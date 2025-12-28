# odznaki/views/tools/orphaned_pois_view.py

from django.shortcuts import render
from odznaki.services import tools_service

def orphaned_pois_auditor_view(request):
    """
    Widok dla narzędzia "Audyt Osieroconych POI".
    """
    results = tools_service.find_orphaned_pois_with_context()
    total_orphans = len(results)

    badge_discrepancies = tools_service.find_badge_poi_count_discrepancies()

    context = {
        'orphaned_poi_data': results,
        'total_orphans_count': total_orphans,
        'badge_discrepancies': badge_discrepancies,
    }

    return render(request, 'odznaki/tools/orphaned_pois.html', context)
