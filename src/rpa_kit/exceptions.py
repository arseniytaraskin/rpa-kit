class RpaError(Exception):
    """Базовая ошибка библиотеки."""
    pass


class FileOperationError(RpaError):
    """Ошибка операции с файлом или каталогом."""
    pass


class ApiError(RpaError):
    """Ошибка HTTP-взаимодействия."""
    pass


class ApiTimeoutError(ApiError):
    """Истек таймаут ожидания сети."""
    pass


class ApiStatusError(ApiError):
    """Сервер вернул HTTP 4xx или 5xx."""

    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"Сервер вернул HTTP {status_code}")


class ApiResponseError(ApiError):
    """Ответ не соответствует ожидаемому формату."""
    pass

class TableOperationError(RpaError):
    """Ошибка обработки таблицы."""
    pass

class BrowserError(RpaError):
    """Ошибка управления браузером."""
    pass


class BrowserTimeoutError(BrowserError):
    """Истекло время ожидания браузера."""
    pass

class LoggingError(RpaError):
    pass

class RunError(RpaError):
    """Ошибка ведения журнала выполнения."""
    pass