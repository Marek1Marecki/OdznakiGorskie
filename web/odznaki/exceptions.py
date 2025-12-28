"""
Moduł zawierający niestandardowe wyjątki dla aplikacji odznaki.
"""

class ApplicationError(Exception):
    """
    Bazowy wyjątek dla wszystkich błędów w logice aplikacji.
    Umożliwia łapanie wszystkich naszych niestandardowych błędów w jednym bloku `except`.
    """
    pass


class ValidationError(ApplicationError):
    """
    Wyjątek rzucany, gdy dane wejściowe nie przechodzą walidacji biznesowej.
    Może zawierać słownik błędów do mapowania na konkretne pola formularza.
    """
    def __init__(self, message, error_dict=None):
        super().__init__(message)
        self.error_dict = error_dict or {}


class BusinessLogicError(ApplicationError):
    """
    Wyjątek dla błędów naruszających reguły biznesowe, które nie są
    prostymi błędami walidacji pól.
    Przykład: Próba wykonania akcji na obiekcie w nieprawidłowym stanie.
    """
    pass

# --- Konkretne, reużywalne wyjątki ---

class DatesNotInSequenceError(ValidationError):
    """Błąd rzucany, gdy daty nie zachowują chronologicznej kolejności."""
    def __init__(self, message="Daty nie są w porządku chronologicznym.", error_dict=None):
        super().__init__(message, error_dict)


class BadgeNotFullyAchievedError(BusinessLogicError):
    """Błąd rzucany przy próbie weryfikacji niezdobytej odznaki."""
    def __init__(self, message="Nie można ustawić daty, ponieważ odznaka nadrzędna nie jest w pełni zdobyta."):
        super().__init__(message)


class MissingRequiredDependencyError(ValidationError):
    """Błąd rzucany, gdy brakuje powiązanego, wymaganego obiektu (np. organizatora)."""
    def __init__(self, message="Brakuje wymaganego obiektu powiązanego.", error_dict=None):
        super().__init__(message, error_dict)
