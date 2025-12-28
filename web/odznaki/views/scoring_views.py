# odznaki/views/scoring_views.py

from django.shortcuts import render
from django.http import JsonResponse
from odznaki.services import scoring_service
from operator import itemgetter


def poi_scores_view(request):
    """
    Widok wyświetlający ranking POI, obsługujący DataTables po stronie serwera.
    """
    all_rankings_data = scoring_service.calculate_all_dashboard_scores(get_full_lists=True)
    full_poi_ranking = all_rankings_data['poi_ranking']

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # This is an AJAX request from Datatables
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')
        order_column_index = int(request.GET.get('order[0][column]', 0))
        order_direction = request.GET.get('order[0][dir]', 'asc')
        
        # Define columns for sorting/searching (must match frontend)
        columns = ['poi', 'score'] # Simplified for now, assuming only these are sortable/searchable

        # Apply filtering
        filtered_data = full_poi_ranking
        if search_value:
            filtered_data = [
                item for item in full_poi_ranking
                if search_value.lower() in item['poi'].name.lower() or \
                   search_value.lower() in str(item['score']).lower()
            ]

        records_filtered = len(filtered_data)

        # Apply sorting
        if order_column_index < len(columns):
            sort_by = columns[order_column_index]
            if sort_by == 'poi': # Sort by POI name
                filtered_data.sort(key=lambda x: x['poi'].name.lower(), reverse=(order_direction == 'desc'))
            elif sort_by == 'score': # Sort by score
                filtered_data.sort(key=itemgetter('score'), reverse=(order_direction == 'desc'))
            # Add more sorting logic for other columns if needed
        
        # Apply pagination
        paginated_data = filtered_data[start:start + length]

        # Format data for Datatables JSON response
        formatted_data = []
        for item in paginated_data:
            formatted_data.append({
                'id': item['poi'].id,
                'name': item['poi'].name,
                'score': round(item['score'], 2),
                'mesoregion': item['poi'].mesoregion.name if item['poi'].mesoregion else '',
                'mesoregion_id': item['poi'].mesoregion.id if item['poi'].mesoregion else None,
                'voivodeship': item['poi'].voivodeship.name if item['poi'].voivodeship else '',
                'voivodeship_id': item['poi'].voivodeship.id if item['poi'].voivodeship else None,
            })

        response_data = {
            "draw": draw,
            "recordsTotal": len(full_poi_ranking),
            "recordsFiltered": records_filtered,
            "data": formatted_data,
        }
        return JsonResponse(response_data)

    else:
        # This is a regular GET request, render the HTML template
        context = {
            'poi_ranking': [], # Datatables will populate this
        }
        return render(request, 'odznaki/poi_scores.html', context)

def mesoregion_scores_view(request):
    """
    Widok wyświetlający ranking mezoregionów, obsługujący DataTables.
    """
    all_rankings_data = scoring_service.calculate_all_dashboard_scores(get_full_lists=True)
    full_region_ranking = all_rankings_data['region_ranking']

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # This is an AJAX request from Datatables
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')
        order_column_index = int(request.GET.get('order[0][column]', 0))
        order_direction = request.GET.get('order[0][dir]', 'asc')
        
        # Define columns for sorting/searching (must match frontend)
        columns = ['mesoregion_name', 'total_score', 'poi_count']

        # Apply filtering
        filtered_data = full_region_ranking
        if search_value:
            filtered_data = [
                item for item in full_region_ranking
                if search_value.lower() in item['mesoregion_name'].lower() or \
                   search_value.lower() in str(item['total_score']).lower() or \
                   search_value.lower() in str(item['poi_count']).lower()
            ]

        records_filtered = len(filtered_data)

        # Apply sorting
        if order_column_index < len(columns):
            sort_by = columns[order_column_index]
            if sort_by == 'mesoregion_name':
                filtered_data.sort(key=lambda x: x['mesoregion_name'].lower(), reverse=(order_direction == 'desc'))
            elif sort_by == 'total_score':
                filtered_data.sort(key=itemgetter('total_score'), reverse=(order_direction == 'desc'))
            elif sort_by == 'poi_count':
                filtered_data.sort(key=itemgetter('poi_count'), reverse=(order_direction == 'desc'))
        
        # Apply pagination
        paginated_data = filtered_data[start:start + length]

        # Format data for Datatables JSON response
        formatted_data = []
        for item in paginated_data:

            # --- NOWA LOGIKA: Ręcznie "spłaszczamy" listę top_pois ---
            top_pois_simple = []
            for poi_item in item['top_pois']:
                top_pois_simple.append({
                    'id': poi_item['poi'].id,
                    'name': poi_item['poi'].name,
                    'score': poi_item['score']
                })
            # --- KONIEC NOWEJ LOGIKI ---

            # Poprawka w logice pobierania mesoregion_id
            mesoregion_id = None
            if item['top_pois']:
                first_poi_item = item['top_pois'][0]
                if first_poi_item['poi'].mesoregion:
                    mesoregion_id = first_poi_item['poi'].mesoregion.id

            formatted_data.append({
                'mesoregion_name': item['mesoregion_name'],
                'mesoregion_id': mesoregion_id,
                'total_score': round(item['total_score'], 2),
                'poi_count': item['poi_count'],
                'top_pois': top_pois_simple,  # <-- Przekazujemy nową, "płaską" listę
            })

        response_data = {
            "draw": draw,
            "recordsTotal": len(full_region_ranking),
            "recordsFiltered": records_filtered,
            "data": formatted_data,
        }
        return JsonResponse(response_data)

    else:
        # This is a regular GET request, render the HTML template
        context = {
            'region_scores': [],
        }
        return render(request, 'odznaki/mesoregion_scores.html', context)
