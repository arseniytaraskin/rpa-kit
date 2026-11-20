from pathlib import Path

import pandas as pd

from rpa_kit.exceptions import TableOperationError
from rpa_kit.tables import (
    filter_rows,
    merge_tables,
    read_excel,
    require_columns,
    write_csv,
    write_excel,
)


PROJECT_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    output = PROJECT_DIR / "output" / "tables_demo"

    try:
        first = pd.DataFrame({
            "ticket_id": ["T-001", "T-002"],
            "service": ["web_search", "exchange_rate"],
            "status": ["done", "pending"],
        })

        second = pd.DataFrame({
            "ticket_id": ["T-003", "T-004"],
            "service": ["excel_merge", "web_search"],
            "status": ["done", "done"],
        })

        first_path = write_excel(
            first,
            output / "first.xlsx",
            overwrite=True,
        )

        second_path = write_excel(
            second,
            output / "second.xlsx",
            overwrite=True,
        )

        tables = [
            read_excel(first_path),
            read_excel(second_path),
        ]

        combined = merge_tables(tables)

        require_columns(
            combined,
            ["ticket_id", "service", "status"],
        )

        completed = filter_rows(
            combined,
            "status",
            "done",
        )

        excel_path = write_excel(
            combined,
            output / "combined.xlsx",
            overwrite=True,
        )

        csv_path = write_csv(
            completed,
            output / "completed.csv",
            overwrite=True,
        )

        print(f"Всего строк: {len(combined)}")
        print(f"Завершённых: {len(completed)}")
        print(f"Общая таблица: {excel_path}")
        print(f"Завершённые: {csv_path}")

        return 0

    except TableOperationError as exc:
        print(f"Ошибка: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())