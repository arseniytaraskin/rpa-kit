import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rpa_kit.exceptions import RpaError


class LoggingError(RpaError):
    pass


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    if not isinstance(name, str) or not name.strip():
        raise LoggingError("Укажите непустое имя журнала")

    return logging.getLogger(name)


def configure_console(
    logger: logging.Logger,
    *,
    level: int = logging.INFO,
) -> None:
    if not isinstance(logger, logging.Logger):
        raise LoggingError("Ожидается logging.Logger")

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    )

    logger.addHandler(handler)
    logger.setLevel(level)


def configure_file(
    logger: logging.Logger,
    path: str | Path,
    *,
    level: int = logging.INFO,
    max_bytes: int = 1_048_576,
    backup_count: int = 5,
) -> Path:
    if not isinstance(logger, logging.Logger):
        raise LoggingError("Ожидается logging.Logger")

    destination = Path(path)

    if (
        not isinstance(max_bytes, int)
        or isinstance(max_bytes, bool)
        or max_bytes <= 0
    ):
        raise LoggingError(
            "max_bytes должен быть положительным целым числом"
        )

    if (
        not isinstance(backup_count, int)
        or isinstance(backup_count, bool)
        or backup_count < 0
    ):
        raise LoggingError(
            "backup_count должен быть неотрицательным целым числом"
        )

    try:
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        handler = RotatingFileHandler(
            destination,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )

        handler.setLevel(level)
        handler.setFormatter(
            logging.Formatter(LOG_FORMAT, DATE_FORMAT)
        )

        logger.addHandler(handler)
        logger.setLevel(level)

    except OSError as exc:
        raise LoggingError(
            f"Не удалось настроить файл журнала: {destination}"
        ) from exc

    return destination


def log_step(
    logger: logging.Logger,
    message: str,
) -> None:
    logger.info(message)


def log_success(
    logger: logging.Logger,
    message: str,
) -> None:
    logger.info(message)


def log_warning(
    logger: logging.Logger,
    message: str,
) -> None:
    logger.warning(message)


def log_error(
    logger: logging.Logger,
    message: str,
    *,
    exception: BaseException | None = None,
) -> None:
    if exception is not None:
        logger.exception(message, exc_info=exception)
    else:
        logger.error(message)


def log_debug(
    logger: logging.Logger,
    message: str,
) -> None:
    logger.debug(message)