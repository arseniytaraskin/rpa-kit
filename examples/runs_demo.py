from pathlib import Path

from rpa_kit.exceptions import FileOperationError
from rpa_kit.files import write_json
from rpa_kit.runs import Run


PROJECT_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    output_dir = PROJECT_DIR / "output" / "runs_demo"

    run = Run(
        "demo_robot",
        output_dir=output_dir,
        metadata={"environment": "local"},
    )

    try:
        run.add_step(
            "Подготовка каталога",
            details={"directory": str(output_dir)},
        )

        result_path = write_json(
            output_dir / "result.json",
            {"status": "ok"},
            overwrite=True,
        )

        run.add_step(
            "Сохранение результата",
            details={"file": str(result_path)},
        )

        run.add_artifact(
            "Результат",
            result_path,
        )

        summary = run.complete()
        report_path = run.save()

        print(f"Статус: {summary['status']}")
        print(f"Длительность: {summary['duration_seconds']} сек.")
        print(f"Отчёт: {report_path}")

        return 0

    except Exception as exc:
        summary = run.fail(
            str(exc),
            error_type=type(exc).__name__,
        )

        report_path = run.save()

        print(f"Статус: {summary['status']}")
        print(f"Отчёт: {report_path}")

        return 1


if __name__ == "__main__":
    raise SystemExit(main())