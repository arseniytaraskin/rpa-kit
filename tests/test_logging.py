import logging

import pytest

from rpa_kit.exceptions import LoggingError
from rpa_kit.logging import (
    configure_console,
    configure_file,
    get_logger,
    log_debug,
    log_error,
    log_step,
    log_success,
    log_warning,
)


@pytest.fixture
def logger():
    current = get_logger("rpa_kit.test")
    current.handlers.clear()
    current.setLevel(logging.NOTSET)

    yield current

    current.handlers.clear()


def test_get_logger(logger):
    assert get_logger("rpa_kit.test") is logger


def test_invalid_logger_name():
    with pytest.raises(LoggingError):
        get_logger("")


def test_console_handler(logger):
    configure_console(logger)

    log_step(logger, "Шаг")
    log_success(logger, "Успех")
    log_warning(logger, "Предупреждение")

    records = [
        record.getMessage()
        for record in logger.handlers[0].records
    ]

    assert "Шаг" in records
    assert "Успех" in records
    assert "Предупреждение" in records


def test_file_handler(logger, tmp_path):
    path = configure_file(
        logger,
        tmp_path / "logs" / "robot.log",
    )

    log_step(logger, "Начало")
    log_success(logger, "Завершение")

    content = path.read_text(encoding="utf-8")

    assert "Начало" in content
    assert "Завершение" in content


def test_file_appends(logger, tmp_path):
    path = configure_file(
        logger,
        tmp_path / "robot.log",
    )

    log_step(logger, "Первый запуск")
    logger.handlers.clear()

    configure_file(logger, path)
    log_step(logger, "Второй запуск")

    content = path.read_text(encoding="utf-8")

    assert "Первый запуск" in content
    assert "Второй запуск" in content


def test_error_with_exception(logger, tmp_path):
    configure_file(
        logger,
        tmp_path / "robot.log",
    )

    try:
        raise ValueError("Тестовая ошибка")
    except ValueError as exc:
        log_error(
            logger,
            "Ошибка выполнения",
            exception=exc,
        )

    content = (tmp_path / "robot.log").read_text(
        encoding="utf-8"
    )

    assert "Ошибка выполнения" in content
    assert "ValueError" in content
    assert "Тестовая ошибка" in content


def test_invalid_file_settings(logger, tmp_path):
    with pytest.raises(LoggingError):
        configure_file(
            logger,
            tmp_path / "robot.log",
            max_bytes=0,
        )

    with pytest.raises(LoggingError):
        configure_file(
            logger,
            tmp_path / "robot.log",
            backup_count=-1,
        )


def test_debug_not_written_at_info_level(logger, tmp_path):
    configure_file(
        logger,
        tmp_path / "robot.log",
        level=logging.INFO,
    )

    log_debug(logger, "Отладка")

    content = (tmp_path / "robot.log").read_text(
        encoding="utf-8"
    )

    assert "Отладка" not in content