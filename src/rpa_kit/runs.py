import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from rpa_kit.exceptions import RpaError


class RunError(RpaError):
    """Ошибка ведения журнала выполнения."""
    pass

class Run:
    def __init__(
        self,
        robot_name: str,
        *,
        output_dir: str | Path,
        metadata: dict[str, Any] | None = None,
    ):
        if not isinstance(robot_name, str) or not robot_name.strip():
            raise RunError("Укажите непустое имя робота")

        if not isinstance(metadata, dict) and metadata is not None:
            raise RunError("metadata должен быть словарём")

        self.robot_name = robot_name.strip()
        self.run_id = uuid4().hex
        self.output_dir = Path(output_dir)
        self.metadata = dict(metadata or {})

        self.status = "running"
        self.started_at = datetime.now(timezone.utc)
        self.finished_at = None
        self.steps: list[dict[str, Any]] = []
        self.artifacts: list[dict[str, str]] = []
        self.error: dict[str, str] | None = None

        self._started_monotonic = time.monotonic()

    @property
    def duration_seconds(self) -> float | None:
        if self.finished_at is None:
            return None

        return round(
            time.monotonic() - self._started_monotonic,
            3,
        )

    def add_step(
        self,
        name: str,
        *,
        status: str = "completed",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(name, str) or not name.strip():
            raise RunError("Укажите непустое имя шага")

        if status not in ("completed", "failed", "skipped"):
            raise RunError(
                "status должен быть completed, failed или skipped"
            )

        if not isinstance(details, dict) and details is not None:
            raise RunError("details должен быть словарём")

        step = {
            "name": name.strip(),
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": dict(details or {}),
        }

        self.steps.append(step)
        return step

    def add_artifact(
        self,
        name: str,
        path: str | Path,
    ) -> dict[str, str]:
        if not isinstance(name, str) or not name.strip():
            raise RunError("Укажите непустое имя артефакта")

        artifact_path = Path(path)

        if not artifact_path.is_absolute():
            artifact_path = (
                self.output_dir / artifact_path
            ).resolve()

        artifact = {
            "name": name.strip(),
            "path": str(artifact_path),
        }

        self.artifacts.append(artifact)
        return artifact

    def complete(self) -> dict[str, Any]:
        if self.status != "running":
            raise RunError("Запуск уже завершён")

        self.status = "completed"
        self.finished_at = datetime.now(timezone.utc)

        return self.to_dict()

    def fail(
        self,
        message: str,
        *,
        error_type: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(message, str) or not message.strip():
            raise RunError("Укажите сообщение об ошибке")

        if self.status != "running":
            raise RunError("Запуск уже завершён")

        self.status = "failed"
        self.finished_at = datetime.now(timezone.utc)

        self.error = {
            "message": message.strip(),
            "type": error_type or type(None).__name__,
        }

        return self.to_dict()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "robot_name": self.robot_name,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "finished_at": (
                self.finished_at.isoformat()
                if self.finished_at
                else None
            ),
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
            "steps": self.steps,
            "artifacts": self.artifacts,
            "error": self.error,
        }

    def save(self, path: str | Path | None = None) -> Path:
        destination = (
            Path(path)
            if path is not None
            else self.output_dir / f"{self.run_id}.json"
        )

        try:
            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with destination.open(
                "w",
                encoding="utf-8",
            ) as stream:
                json.dump(
                    self.to_dict(),
                    stream,
                    ensure_ascii=False,
                    indent=2,
                )

        except (OSError, TypeError, ValueError) as exc:
            raise RunError(
                f"Не удалось сохранить журнал: {destination}"
            ) from exc

        return destination