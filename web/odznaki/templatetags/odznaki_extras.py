# odznaki/templatetags/odznaki_extras.py
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def get_status_display_for_filter(status_key):
    """
    Zwraca czytelną dla użytkownika nazwę statusu na podstawie klucza.
    np. 'w_trakcie' -> 'W trakcie'
    """
    statuses = {
        'zdobyty': 'Zdobyty',
        'w_trakcie': 'W trakcie',
        'niezdobyty': 'Do zdobycia',
        'nieaktywny': 'Nieaktywny',
        'do_ponowienia': 'Do ponowienia', # Dodajmy też nasz nowy status
    }
    # Używamy .title() jako fallback, jeśli klucz nie zostanie znaleziony
    return statuses.get(status_key, str(status_key).replace('_', ' ').title())


@register.filter
def map_attribute(objects, attribute):
    """
    Pobiera atrybut z każdego obiektu na liście.
    Umożliwia zagnieżdżone odwołania, np. 'poi.id'.
    """
    if not objects:
        return []
    
    keys = attribute.split('.')
    result = []
    for obj in objects:
        val = obj
        for key in keys:
            # Sprawdzamy, czy `val` jest słownikiem czy obiektem
            if isinstance(val, dict):
                val = val.get(key)
            elif hasattr(val, key):
                val = getattr(val, key)
            else:
                val = None
                break
        if val is not None:
            result.append(val)
    return result


@register.filter
def progress_bar_style(percentage):
    """
    Generuje styl CSS dla paska postępu z płynnym gradientem kolorów.
    Poprawnie obsługuje liczby zmiennoprzecinkowe.
    """
    try:
        # Konwertujemy na float, aby zachować precyzję
        p = float(percentage or 0)
    except (ValueError, TypeError):
        p = 0

    # Ograniczamy wartość do zakresu 0-100, ale NADAL jako float
    p = max(0.0, min(p, 100.0))

    # Obliczamy odcień, operując na float
    hue = p * 1.2

    saturation = 80
    lightness = 45

    # Formujemy styl, zaokrąglając hue do 1 miejsca po przecinku dla bezpieczeństwa
    style = f"background-color: hsl({hue:.1f}, {saturation}%, {lightness}%);"

    return mark_safe(style)


@register.filter
def model_name(obj):
    """Zwraca nazwę modelu danego obiektu, małymi literami."""
    if hasattr(obj, '_meta'):
        return obj._meta.model_name
    return ''


@register.filter
def sub(value, arg):
    """
    Odejmuje argument od wartości. Używane do przełączania flag 0/1.
    Przykład: {{ 1|sub:my_variable }}
    """
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return value


@register.filter
def urlencode_without(querydict, key_to_remove):
    """
    Przyjmuje QueryDict (np. request.GET), usuwa z niego podany klucz
    i zwraca resztę jako string URL-encoded.
    """
    # Kopiujemy QueryDict, aby go nie modyfikować
    params = querydict.copy()
    if key_to_remove in params:
        del params[key_to_remove]
    # .urlencode() zamienia słownik na string "key1=val1&key2=val2"
    return params.urlencode()
