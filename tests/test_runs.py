import json

import pytest

from rpa_kit.exceptions import RunError
from rpa_kit.runs import Run


@pytest.fixture
def run(tmp_path):
    return Run(
        "test_robot",
        output_dir=tmp_path,
        metadata={"env": "test"},
    )


def test_run_initial_state(run):
    data = run.to_dict()

    assert run.robot_name == "test_robot"
    assert run.status == "running"
    assert data["metadata"] == {"env": "test"}
    assert data["steps"] == []
    assert data["artifacts"] == []
    assert data["error"] is None


def test_add_step(run):
    step = run.add_step(
        "Чтение файла",
        details={"file": "input.xlsx"},
    )

    assert step["name"] == "Чтение файла"
    assert step["status"] == "completed"
    assert step["details"] == {"file": "input.xlsx"}
    assert len(run.steps) == 1


def test_invalid_step_status(run):
    with pytest.raises(RunError):
        run.add_step("Шаг", status="unknown")


def test_add_artifact(run, tmp_path):
    artifact = run.add_artifact(
        "Отчёт",
        tmp_path / "report.json",
    )

    assert artifact["name"] == "Отчёт"
    assert artifact["path"].endswith("report.json")
    assert len(run.artifacts) == 1


def test_complete(run):
    run.add_step("Шаг")

    summary = run.complete()

    assert summary["status"] == "completed"
    assert summary["finished_at"] is not None
    assert summary["duration_seconds"] >= 0


def test_fail(run):
    summary = run.fail(
        "Не удалось открыть файл",
        error_type="FileOperationError",
    )

    assert summary["status"] == "failed"
    assert summary["error"]["message"] == "Не удалось открыть файл"
    assert summary["error"]["type"] == "FileOperationError"


def test_cannot_complete_twice(run):
    run.complete()

    with pytest.raises(RunError):
        run.complete()


def test_cannot_fail_after_complete(run):
    run.complete()

    with pytest.raises(RunError):
        run.fail("Ошибка")


def test_save_default_path(run, tmp_path):
    run.add_step("Шаг")
    run.complete()

    path = run.save()

    assert path.parent == tmp_path
    assert path.suffix == ".json"

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert data["status"] == "completed"
    assert data["steps"][0]["name"] == "Шаг"


def test_save_custom_path(run, tmp_path):
    path = tmp_path / "reports" / "custom.json"

    run.complete()
    saved = run.save(path)

    assert saved == path
    assert path.is_file()


def test_invalid_robot_name(tmp_path):
    with pytest.raises(RunError):
        Run("   ", output_dir=tmp_path)