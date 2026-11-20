import math
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

from rpa_kit.exceptions import (
    RetryError,
    RetryTimeoutError,
)


T = TypeVar("T")


def validate_positive_number(
    value: Any,
    name: str,
) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(
            f"{name} должен быть положительным числом"
        )

    return float(value)


def validate_non_negative_number(
    value: Any,
    name: str,
) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(
            f"{name} должен быть неотрицательным числом"
        )

    return float(value)


def calculate_delay(
    attempt: int,
    *,
    strategy: str,
    base_delay: float,
    max_delay: float,
    multiplier: float,
    jitter: float,
) -> float:
    if attempt < 1:
        raise ValueError("attempt должен быть не меньше 1")

    if strategy == "fixed":
        delay = base_delay

    elif strategy == "linear":
        delay = base_delay * attempt

    elif strategy == "exponential":
        delay = base_delay * (
            multiplier ** (attempt - 1)
        )

    else:
        raise ValueError(
            "strategy должен быть fixed, linear или exponential"
        )

    delay = min(delay, max_delay)

    if jitter:
        delay += random.uniform(0, jitter)

    return min(delay, max_delay)


def retry(
    operation: Callable[[], T],
    *,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    max_attempts: int = 3,
    strategy: str = "exponential",
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    multiplier: float = 2.0,
    jitter: float = 0.0,
    total_timeout: float | None = None,
    on_retry: Callable[[int, BaseException], None] | None = None,
) -> T:
    """Выполняет операцию с повторными попытками.

    Повторяются только исключения из exceptions.
    """

    if not callable(operation):
        raise ValueError("operation должна быть функцией")

    if (
        not isinstance(max_attempts, int)
        or isinstance(max_attempts, bool)
        or max_attempts < 1
    ):
        raise ValueError(
            "max_attempts должен быть целым числом не меньше 1"
        )

    if not exceptions:
        raise ValueError(
            "Укажите хотя бы одно исключение для повтора"
        )

    base_delay = validate_positive_number(
        base_delay,
        "base_delay",
    )

    max_delay = validate_positive_number(
        max_delay,
        "max_delay",
    )

    multiplier = validate_positive_number(
        multiplier,
        "multiplier",
    )

    jitter = validate_non_negative_number(
        jitter,
        "jitter",
    )

    if strategy not in ("fixed", "linear", "exponential"):
        raise ValueError(
            "strategy должен быть fixed, linear или exponential"
        )

    if total_timeout is not None:
        total_timeout = validate_positive_number(
            total_timeout,
            "total_timeout",
        )

    started_at = time.monotonic()
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()

        except exceptions as error:
            last_error = error

            if on_retry is not None:
                on_retry(attempt, error)

            if attempt == max_attempts:
                break

            if total_timeout is not None:
                elapsed = time.monotonic() - started_at

                if elapsed >= total_timeout:
                    raise RetryTimeoutError(
                        f"Истекло время повторных попыток: "
                        f"{total_timeout} сек."
                    ) from error

            delay = calculate_delay(
                attempt,
                strategy=strategy,
                base_delay=base_delay,
                max_delay=max_delay,
                multiplier=multiplier,
                jitter=jitter,
            )

            if total_timeout is not None:
                remaining = (
                    total_timeout
                    - (time.monotonic() - started_at)
                )

                if remaining <= 0:
                    raise RetryTimeoutError(
                        f"Истекло время повторных попыток: "
                        f"{total_timeout} сек."
                    ) from error

                delay = min(delay, remaining)

            time.sleep(delay)

    raise RetryError(
        f"Не удалось выполнить операцию за {max_attempts} попыток"
    ) from last_error


def retry_async_like(
    operation: Callable[[], T],
    *,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    max_attempts: int = 3,
    strategy: str = "exponential",
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    multiplier: float = 2.0,
    jitter: float = 0.0,
    total_timeout: float | None = None,
    on_retry: Callable[[int, BaseException], None] | None = None,
) -> T:
    """Псевдоним retry для единообразного API."""

    return retry(
        operation,
        exceptions=exceptions,
        max_attempts=max_attempts,
        strategy=strategy,
        base_delay=base_delay,
        max_delay=max_delay,
        multiplier=multiplier,
        jitter=jitter,
        total_timeout=total_timeout,
        on_retry=on_retry,
    )


def with_retry(
    *,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    max_attempts: int = 3,
    strategy: str = "exponential",
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    multiplier: float = 2.0,
    jitter: float = 0.0,
    total_timeout: float | None = None,
    on_retry: Callable[[int, BaseException], None] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Декоратор для повторного вызова функции."""

    def decorator(
        function: Callable[..., T],
    ) -> Callable[..., T]:
        def wrapper(
            *args: Any,
            **kwargs: Any,
        ) -> T:
            def operation() -> T:
                return function(*args, **kwargs)

            return retry(
                operation,
                exceptions=exceptions,
                max_attempts=max_attempts,
                strategy=strategy,
                base_delay=base_delay,
                max_delay=max_delay,
                multiplier=multiplier,
                jitter=jitter,
                total_timeout=total_timeout,
                on_retry=on_retry,
            )

        return wrapper

    return decorator