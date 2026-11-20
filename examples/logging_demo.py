from pathlib import Path

from rpa_kit.exceptions import FileOperationError
from rpa_kit.logging import (
    configure_console,
    configure_file,
    get_logger,
    log_error,
    log_step,
    log_success,
    log_warning,
    log_debug
)


PROJECT_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    logger = get_logger("rpa_kit.demo")

    try:
        log_path = configure_file(
            logger,
            PROJECT_DIR / "output" / "logs" / "robot.log",
        )

        configure_console(logger)

        log_step(logger, "Запуск демонстрационного робота")
        log_debug(logger, "Подробная отладочная информация")
        log_warning(logger, "Предупреждение: демонстрационный запуск")
        log_success(logger, "Демонстрация завершена")

        return 0

    except Exception as exc:
        log_error(
            logger,
            "Демонстрация завершилась с ошибкой",
            exception=exc,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())