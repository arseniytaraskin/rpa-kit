class RpaError(Exception):
    """Базовая ошибка библиотеки."""


class FileOperationError(RpaError):
    """Ошибка операции с файлом или каталогом."""


class ApiError(RpaError):
    """Ошибка HTTP-взаимодействия."""


class ApiTimeoutError(ApiError):
    """Истек таймаут ожидания сети."""


class ApiStatusError(ApiError):
    """Сервер вернул HTTP 4xx или 5xx."""

    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"Сервер вернул HTTP {status_code}")


class ApiResponseError(ApiError):
    """Ответ не соответствует ожидаемому формату."""