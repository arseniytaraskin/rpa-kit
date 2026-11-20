import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from rpa_kit.exceptions import ConfigError


ENV_KEY_PATTERN = re.compile(
    r"^[A-Z][A-Z0-9_]*$"
)


def validate_env_key(key: str) -> str:
    if not isinstance(key, str) or not ENV_KEY_PATTERN.fullmatch(key):
        raise ConfigError(
            f"Некорректное имя переменной окружения: {key}"
        )

    return key


def load_env(
    path: str | Path | None = None,
    *,
    override: bool = False,
) -> list[str]:
    if path is not None:
        source = Path(path)

        if not source.is_file():
            raise ConfigError(
                f"Файл .env не найден: {source}"
            )

        load_dotenv(
            source,
            override=override,
        )

        return [source.name]

    load_dotenv(override=override)

    return [".env"]


def get_env(
    key: str,
    *,
    default: str | None = None,
) -> str | None:
    key = validate_env_key(key)

    value = os.getenv(key, default)

    if value is None:
        return None

    return value.strip()


def require_env(key: str) -> str:
    value = get_env(key)

    if not value:
        raise ConfigError(
            f"Не задана обязательная переменная окружения: {key}"
        )

    return value


def get_bool(
    key: str,
    *,
    default: bool = False,
) -> bool:
    value = get_env(key)

    if value is None:
        return default

    normalized = value.lower()

    if normalized in ("1", "true", "yes", "on"):
        return True

    if normalized in ("0", "false", "no", "off"):
        return False

    raise ConfigError(
        f"Переменная {key} должна быть true или false"
    )


def get_int(
    key: str,
    *,
    default: int | None = None,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    value = get_env(key)

    if value is None:
        if default is None:
            raise ConfigError(
                f"Не задана переменная окружения: {key}"
            )

        return default

    try:
        result = int(value)
    except ValueError as exc:
        raise ConfigError(
            f"Переменная {key} должна быть целым числом"
        ) from exc

    if minimum is not None and result < minimum:
        raise ConfigError(
            f"Переменная {key} должна быть не меньше {minimum}"
        )

    if maximum is not None and result > maximum:
        raise ConfigError(
            f"Переменная {key} должна быть не больше {maximum}"
        )

    return result


def get_float(
    key: str,
    *,
    default: float | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    value = get_env(key)

    if value is None:
        if default is None:
            raise ConfigError(
                f"Не задана переменная окружения: {key}"
            )

        return default

    try:
        result = float(value)
    except ValueError as exc:
        raise ConfigError(
            f"Переменная {key} должна быть числом"
        ) from exc

    if minimum is not None and result < minimum:
        raise ConfigError(
            f"Переменная {key} должна быть не меньше {minimum}"
        )

    if maximum is not None and result > maximum:
        raise ConfigError(
            f"Переменная {key} должна быть не больше {maximum}"
        )

    return result


def get_list(
    key: str,
    *,
    separator: str = ",",
    default: list[str] | None = None,
) -> list[str]:
    if not separator:
        raise ConfigError("Укажите разделитель")

    value = get_env(key)

    if value is None:
        return list(default or [])

    return [
        item.strip()
        for item in value.split(separator)
        if item.strip()
    ]


def get_path(
    key: str,
    *,
    default: str | Path | None = None,
    must_exist: bool = False,
) -> Path:
    value = get_env(key)

    if value is None:
        if default is None:
            raise ConfigError(
                f"Не задана переменная окружения: {key}"
            )

        value = str(default)

    path = Path(value)

    if must_exist and not path.exists():
        raise ConfigError(
            f"Путь из переменной {key} не существует: {path}"
        )

    return path


def read_json(
    path: str | Path,
) -> dict[str, Any]:
    source = Path(path)

    if not source.is_file():
        raise ConfigError(
            f"JSON-файл конфигурации не найден: {source}"
        )

    try:
        with source.open(
            encoding="utf-8",
        ) as stream:
            data = json.load(stream)

    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(
            f"Не удалось прочитать JSON: {source}"
        ) from exc

    if not isinstance(data, dict):
        raise ConfigError(
            f"JSON должен содержать объект: {source}"
        )

    return data


def mask_secret(value: str | None) -> str:
    if not value:
        return ""

    if len(value) <= 4:
        return "****"

    return f"{value[:2]}****{value[-2:]}"


class RobotConfig:
    def __init__(
        self,
        *,
        env_file: str | Path | None = None,
        json_file: str | Path | None = None,
        override_env: bool = False,
    ):
        self._values: dict[str, Any] = {}

        if env_file is not None:
            load_env(
                env_file,
                override=override_env,
            )

        if json_file is not None:
            self._values.update(
                read_json(json_file)
            )

    def get(
        self,
        key: str,
        *,
        default: Any = None,
    ) -> Any:
        env_key = key.upper()

        if env_key in os.environ:
            return os.environ[env_key]

        if key in self._values:
            return self._values[key]

        return default

    def require(self, key: str) -> Any:
        value = self.get(key)

        if value is None or value == "":
            raise ConfigError(
                f"Не задана обязательная настройка: {key}"
            )

        return value

    def get_str(
        self,
        key: str,
        *,
        default: str | None = None,
    ) -> str:
        value = self.get(key, default=default)

        if value is None:
            return ""

        return str(value).strip()

    def get_bool(
        self,
        key: str,
        *,
        default: bool = False,
    ) -> bool:
        value = self.get(key)

        if value is None:
            return default

        if isinstance(value, bool):
            return value

        normalized = str(value).strip().lower()

        if normalized in ("1", "true", "yes", "on"):
            return True

        if normalized in ("0", "false", "no", "off"):
            return False

        raise ConfigError(
            f"Настройка {key} должна быть true или false"
        )

    def get_int(
        self,
        key: str,
        *,
        default: int | None = None,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int:
        value = self.get(key)

        if value is None:
            if default is None:
                raise ConfigError(
                    f"Не задана настройка: {key}"
                )

            return default

        try:
            result = int(value)
        except (TypeError, ValueError) as exc:
            raise ConfigError(
                f"Настройка {key} должна быть целым числом"
            ) from exc

        if minimum is not None and result < minimum:
            raise ConfigError(
                f"Настройка {key} должна быть не меньше {minimum}"
            )

        if maximum is not None and result > maximum:
            raise ConfigError(
                f"Настройка {key} должна быть не больше {maximum}"
            )

        return result

    def get_float(
        self,
        key: str,
        *,
        default: float | None = None,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> float:
        value = self.get(key)

        if value is None:
            if default is None:
                raise ConfigError(
                    f"Не задана настройка: {key}"
                )

            return default

        try:
            result = float(value)
        except (TypeError, ValueError) as exc:
            raise ConfigError(
                f"Настройка {key} должна быть числом"
            ) from exc

        if minimum is not None and result < minimum:
            raise ConfigError(
                f"Настройка {key} должна быть не меньше {minimum}"
            )

        if maximum is not None and result > maximum:
            raise ConfigError(
                f"Настройка {key} должна быть не больше {maximum}"
            )

        return result

    def get_list(
        self,
        key: str,
        *,
        separator: str = ",",
        default: list[str] | None = None,
    ) -> list[str]:
        value = self.get(key)

        if value is None:
            return list(default or [])

        if isinstance(value, list):
            return [
                str(item).strip()
                for item in value
                if str(item).strip()
            ]

        return [
            item.strip()
            for item in str(value).split(separator)
            if item.strip()
        ]

    def get_path(
        self,
        key: str,
        *,
        default: str | Path | None = None,
        must_exist: bool = False,
    ) -> Path:
        value = self.get(key)

        if value is None:
            if default is None:
                raise ConfigError(
                    f"Не задана настройка: {key}"
                )

            value = default

        path = Path(str(value))

        if must_exist and not path.exists():
            raise ConfigError(
                f"Путь из настройки {key} не существует: {path}"
            )

        return path

    def require_all(
        self,
        keys: list[str],
    ) -> None:
        missing = [
            key
            for key in keys
            if self.get(key) in (None, "")
        ]

        if missing:
            raise ConfigError(
                "Отсутствуют обязательные настройки: "
                + ", ".join(missing)
            )

    def to_dict(
        self,
        *,
        mask_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        mask_keys = mask_keys or []

        result = dict(self._values)

        for key in os.environ:
            if key.lower() in {
                item.lower()
                for item in mask_keys
            }:
                result[key] = mask_secret(
                    os.environ[key]
                )
            else:
                result[key] = os.environ[key]

        for key, value in self._values.items():
            if key.lower() in {
                item.lower()
                for item in mask_keys
            }:
                result[key] = mask_secret(
                    str(value)
                )

        return result