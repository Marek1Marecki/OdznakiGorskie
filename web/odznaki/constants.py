# odznaki/constants.py

"""
Moduł do przechowywania stałych i konfiguracji na poziomie aplikacji.
"""

# Definicja łańcuchów górskich przez ich GŁÓWNE jednostki składowe (Prowincje, Podprowincje).
# Wartości w listach to ID obiektów z bazy danych.
MOUNTAIN_RANGES = {
    'karpaty': {
        'name': 'Karpaty',
        'slug': 'karpaty',
        'wiki_link': 'https://pl.wikipedia.org/wiki/Karpaty',
        'description': 'Łańcuch górski w środkowej Europie...',

        # Definiujemy Karpaty przez ID ich głównych Prowincji i/lub Podprowincji
        'province_ids': [2, 3, 22, 23, 26],
        'subprovince_ids': [],
        'macroregion_ids': [],
    },
    'sudety': {
        'name': 'Sudety',
        'slug': 'sudety',
        'wiki_link': 'https://pl.wikipedia.org/wiki/Sudety',
        'description': 'Łańcuch górski na terenie Czech, Polski i Niemiec...',

        # Sudety można zdefiniować przez jedną Prowincję
        'province_ids': [6, 20],
        'subprovince_ids': [],
        'macroregion_ids': [],
    }
}