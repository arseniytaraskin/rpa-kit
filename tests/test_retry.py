import pytest

from rpa_kit.exceptions import (
    ApiError,
    RetryError,
    RetryTimeoutError,
)
from rpa_kit.retry import (
    calculate_delay,
    retry,
    with_retry,
)


def test_success_on_first_attempt():
    result = retry(
        lambda: "ok",
        exceptions=(ApiError,),
        max_attempts=3,
        base_delay=0.01,
    )

    assert result == "ok"


def test_success_after_failures():
    calls = []

    def operation():
        calls.append(1)

        if len(calls) < 3:
            raise ApiError("Временная ошибка")

        return "готово"

    result = retry(
        operation,
        exceptions=(ApiError,),
        max_attempts=5,
        base_delay=0.01,
    )

    assert result == "готово"
    assert len(calls) == 3


def test_retry_error_after_attempts():
    def operation():
        raise ApiError("Ошибка")

    with pytest.raises(RetryError):
        retry(
            operation,
            exceptions=(ApiError,),
            max_attempts=3,
            base_delay=0.01,
        )


def test_unexpected_exception_not_retried():
    def operation():
        raise ValueError("Не повторяемая ошибка")

    with pytest.raises(ValueError):
        retry(
            operation,
            exceptions=(ApiError,),
            max_attempts=3,
            base_delay=0.01,
        )


def test_on_retry_called():
    attempts = []

    def operation():
        raise ApiError("Ошибка")

    with pytest.raises(RetryError):
        retry(
            operation,
            exceptions=(ApiError,),
            max_attempts=3,
            base_delay=0.01,
            on_retry=lambda attempt, error: attempts.append(
                attempt
            ),
        )

    assert attempts == [1, 2, 3]


def test_fixed_delay():
    assert calculate_delay(
        1,
        strategy="fixed",
        base_delay=2,
        max_delay=10,
        multiplier=2,
        jitter=0,
    ) == 2

    assert calculate_delay(
        3,
        strategy="fixed",
        base_delay=2,
        max_delay=10,
        multiplier=2,
        jitter=0,
    ) == 2


def test_linear_delay():
    assert calculate_delay(
        1,
        strategy="linear",
        base_delay=1,
        max_delay=10,
        multiplier=2,
        jitter=0,
    ) == 1

    assert calculate_delay(
        3,
        strategy="linear",
        base_delay=1,
        max_delay=10,
        multiplier=2,
        jitter=0,
    ) == 3


def test_exponential_delay():
    assert calculate_delay(
        1,
        strategy="exponential",
        base_delay=1,
        max_delay=100,
        multiplier=2,
        jitter=0,
    ) == 1

    assert calculate_delay(
        2,
        strategy="exponential",
        base_delay=1,
        max_delay=100,
        multiplier=2,
        jitter=0,
    ) == 2

    assert calculate_delay(
        3,
        strategy="exponential",
        base_delay=1,
        max_delay=100,
        multiplier=2,
        jitter=0,
    ) == 4


def test_max_delay():
    assert calculate_delay(
        10,
        strategy="exponential",
        base_delay=1,
        max_delay=5,
        multiplier=2,
        jitter=0,
    ) == 5


def test_invalid_strategy():
    with pytest.raises(ValueError):
        calculate_delay(
            1,
            strategy="unknown",
            base_delay=1,
            max_delay=10,
            multiplier=2,
            jitter=0,
        )


def test_invalid_attempts():
    with pytest.raises(ValueError):
        retry(
            lambda: "ok",
            max_attempts=0,
            base_delay=0.01,
        )


def test_timeout():
    def operation():
        raise ApiError("Ошибка")

    with pytest.raises(RetryTimeoutError):
        retry(
            operation,
            exceptions=(ApiError,),
            max_attempts=10,
            base_delay=1,
            total_timeout=0.01,
        )


def test_decorator():
    calls = []

    @with_retry(
        exceptions=(ApiError,),
        max_attempts=3,
        base_delay=0.01,
    )
    def operation(value: str) -> str:
        calls.append(value)

        if len(calls) < 2:
            raise ApiError("Ошибка")

        return value

    assert operation("тест") == "тест"
    assert calls == ["тест", "тест"]