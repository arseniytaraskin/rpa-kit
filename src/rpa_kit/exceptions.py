class RpaError(Exception):
    """Базовая ошибка библиотеки."""


class FileOperationError(RpaError):
    """Ошибка операции с файлом или каталогом."""
