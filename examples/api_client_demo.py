import json
from pathlib import Path

from rpa_kit.api_client import ApiClient
from rpa_kit.exceptions import ApiError, FileOperationError
from rpa_kit.files import write_json


PROJECT_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        with ApiClient() as client:
            result = client.get_json(
                "https://api.frankfurter.dev/v2/rate/usd/eur"
            )

        output_path = write_json(
            PROJECT_DIR / "output" / "exchange_rate.json",
            result,
            overwrite=True,
        )

        print("Ответ API:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"\nСохранено: {output_path}")

        return 0

    except (ApiError, FileOperationError) as exc:
        print(f"Ошибка: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())