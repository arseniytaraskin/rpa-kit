import random

from rpa_kit.exceptions import ApiError
from rpa_kit.retry import retry


def unstable_api_call() -> str:
    if random.random() < 0.7:
        raise ApiError("Временная ошибка API")

    return "Операция выполнена"


def main() -> int:
    attempts = []

    try:
        result = retry(
            unstable_api_call,
            exceptions=(ApiError,),
            max_attempts=5,
            strategy="exponential",
            base_delay=0.2,
            max_delay=2.0,
            jitter=0.1,
            on_retry=lambda attempt, error: attempts.append(
                attempt
            ),
        )

        print(result)
        print(f"Повторов: {len(attempts)}")

        return 0

    except Exception as exc:
        print(f"Ошибка: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())