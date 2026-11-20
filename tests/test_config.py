import json

import pytest

from rpa_kit.config import (
    RobotConfig,
    get_bool,
    get_env,
    get_int,
    get_list,
    get_path,
    mask_secret,
    read_json,
    require_env,
    validate_env_key,
)
from rpa_kit.exceptions import ConfigError


def test_validate_env_key():
    assert validate_env_key("ROBOT_NAME") == "ROBOT_NAME"


@pytest.mark.parametrize(
    "key",
    ["", "robot", "1ROBOT", "ROBOT-NAME"],
)
def test_invalid_env_key(key):
    with pytest.raises(ConfigError):
        validate_env_key(key)


def test_get_env(monkeypatch):
    monkeypatch.setenv("RPA_TEST_VALUE", "  значение  ")

    assert get_env("RPA_TEST_VALUE") == "значение"


def test_require_env(monkeypatch):
    monkeypatch.setenv("RPA_TEST_REQUIRED", "значение")

    assert require_env("RPA_TEST_REQUIRED") == "значение"


def test_missing_required_env():
    with pytest.raises(ConfigError):
        require_env("RPA_TEST_MISSING")


def test_get_bool(monkeypatch):
    monkeypatch.setenv("RPA_TEST_BOOL", "yes")

    assert get_bool("RPA_TEST_BOOL") is True


def test_invalid_bool(monkeypatch):
    monkeypatch.setenv("RPA_TEST_BOOL", "maybe")

    with pytest.raises(ConfigError):
        get_bool("RPA_TEST_BOOL")


def test_get_int_bounds(monkeypatch):
    monkeypatch.setenv("RPA_TEST_INT", "5")

    assert get_int(
        "RPA_TEST_INT",
        minimum=1,
        maximum=10,
    ) == 5


def test_invalid_int(monkeypatch):
    monkeypatch.setenv("RPA_TEST_INT", "abc")

    with pytest.raises(ConfigError):
        get_int("RPA_TEST_INT")


def test_get_list(monkeypatch):
    monkeypatch.setenv(
        "RPA_TEST_LIST",
        "a, b , ,c",
    )

    assert get_list("RPA_TEST_LIST") == [
        "a",
        "b",
        "c",
    ]


def test_get_path(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "RPA_TEST_PATH",
        str(tmp_path),
    )

    assert get_path(
        "RPA_TEST_PATH",
        must_exist=True,
    ) == tmp_path


def test_missing_path(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "RPA_TEST_PATH",
        str(tmp_path / "missing"),
    )

    with pytest.raises(ConfigError):
        get_path(
            "RPA_TEST_PATH",
            must_exist=True,
        )


def test_read_json(tmp_path):
    path = tmp_path / "config.json"

    path.write_text(
        json.dumps({"robot_name": "demo"}),
        encoding="utf-8",
    )

    assert read_json(path) == {
        "robot_name": "demo"
    }


def test_read_invalid_json(tmp_path):
    path = tmp_path / "config.json"

    path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(ConfigError):
        read_json(path)


def test_mask_secret():
    assert mask_secret("very_long_secret") == "ve****et"
    assert mask_secret("abc") == "****"
    assert mask_secret(None) == ""


def test_robot_config_json(tmp_path):
    path = tmp_path / "robot.json"

    path.write_text(
        json.dumps(
            {
                "robot_name": "demo",
                "robot_timeout": 30,
                "allowed_services": [
                    "web_search"
                ],
            }
        ),
        encoding="utf-8",
    )

    config = RobotConfig(json_file=path)

    assert config.get_str("robot_name") == "demo"
    assert config.get_int("robot_timeout") == 30
    assert config.get_list("allowed_services") == [
        "web_search"
    ]


def test_robot_config_env_priority(tmp_path, monkeypatch):
    path = tmp_path / "robot.json"

    path.write_text(
        json.dumps({"robot_name": "from_json"}),
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "ROBOT_NAME",
        "from_env",
    )

    config = RobotConfig(json_file=path)

    assert config.get_str("robot_name") == "from_env"


def test_require_all(tmp_path):
    path = tmp_path / "robot.json"

    path.write_text(
        json.dumps({"robot_name": "demo"}),
        encoding="utf-8",
    )

    config = RobotConfig(json_file=path)

    with pytest.raises(ConfigError):
        config.require_all(
            ["robot_name", "api_token"]
        )


def test_masked_config(tmp_path, monkeypatch):
    path = tmp_path / "robot.json"

    path.write_text(
        json.dumps({"api_token": "super_secret"}),
        encoding="utf-8",
    )

    config = RobotConfig(json_file=path)

    masked = config.to_dict(
        mask_keys=["api_token"]
    )

    assert masked["api_token"] != "super_secret"
    assert "****" in masked["api_token"]