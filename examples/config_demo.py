from pathlib import Path

from rpa_kit.config import RobotConfig
from rpa_kit.exceptions import ConfigError


PROJECT_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        config = RobotConfig(
            json_file=PROJECT_DIR / "config" / "robot.json",
        )

        robot_name = config.get_str(
            "robot_name",
            default="unnamed_robot",
        )

        headless = config.get_bool(
            "robot_headless",
            default=False,
        )

        timeout = config.get_int(
            "robot_timeout",
            default=30,
            minimum=1,
        )

        output_dir = config.get_path(
            "output_dir",
            default=PROJECT_DIR / "output",
        )

        services = config.get_list(
            "allowed_services",
        )

        api_token = config.get("API_TOKEN")

        print(f"Робот: {robot_name}")
        print(f"Headless: {headless}")
        print(f"Таймаут: {timeout}")
        print(f"Каталог: {output_dir}")
        print(f"Сервисы: {services}")
        print(f"API_TOKEN: {'задан' if api_token else 'не задан'}")

        config.require_all(
            ["robot_name", "output_dir"]
        )

        return 0

    except ConfigError as exc:
        print(f"Ошибка конфигурации: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())