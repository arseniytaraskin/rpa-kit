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

class EmailError(RpaError):
    """Ошибка работы с электронной почтой."""
    pass


class EmailTimeoutError(EmailError):
    """Истекло время ожидания почтового сервера."""
    pass


class EmailAuthenticationError(EmailError):
    """Не удалось авторизоваться на почтовом сервере."""
    pass

class DatabaseError(RpaError):
    """Ошибка работы с базой данных."""
    pass

class OracleDatabaseError(RpaError):
    """Ошибка работы с Oracle Database."""
    pass


class OracleConnectionError(OracleDatabaseError):
    """Не удалось подключиться к Oracle Database."""
    pass


class OracleAuthenticationError(OracleConnectionError):
    """Не удалось авторизоваться в Oracle Database."""
    pass

class ConfigError(RpaError):
    """Ошибка конфигурации робота."""
    pass


class RetryError(RpaError):
    """Исчерпаны попытки выполнения операции."""
    pass


class RetryTimeoutError(RetryError):
    """Истекло время, отведённое на повторные попытки."""
    pass