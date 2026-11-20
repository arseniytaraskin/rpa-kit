from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from rpa_kit.exceptions import TableOperationError


def read_excel(
    path: str | Path,
    *,
    sheet_name: str | int = 0,
    dtype: Any = None,
) -> pd.DataFrame:
    source = Path(path)

    if not isinstance(sheet_name, (str, int)):
        raise TableOperationError(
            "Укажите имя или номер одного листа"
        )

    try:
        return pd.read_excel(
            source,
            sheet_name=sheet_name,
            dtype=dtype,
            engine="openpyxl",
        )
    except Exception as exc:
        raise TableOperationError(
            f"Не удалось прочитать Excel: {source}"
        ) from exc


def read_csv(
    path: str | Path,
    *,
    sep: str = ",",
    encoding: str = "utf-8-sig",
    dtype: Any = None,
) -> pd.DataFrame:
    source = Path(path)

    try:
        return pd.read_csv(
            source,
            sep=sep,
            encoding=encoding,
            dtype=dtype,
        )
    except Exception as exc:
        raise TableOperationError(
            f"Не удалось прочитать CSV: {source}"
        ) from exc


def write_excel(
    table: pd.DataFrame,
    path: str | Path,
    *,
    sheet_name: str = "Data",
    overwrite: bool = False,
) -> Path:
    destination = Path(path)

    if destination.suffix.lower() != ".xlsx":
        raise TableOperationError(
            "Для Excel используйте расширение .xlsx"
        )

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        mode = "wb" if overwrite else "xb"

        with destination.open(mode) as stream:
            table.to_excel(
                stream,
                sheet_name=sheet_name,
                index=False,
                engine="openpyxl",
            )

    except Exception as exc:
        raise TableOperationError(
            f"Не удалось записать Excel: {destination}"
        ) from exc

    return destination


def write_csv(
    table: pd.DataFrame,
    path: str | Path,
    *,
    sep: str = ",",
    encoding: str = "utf-8-sig",
    overwrite: bool = False,
) -> Path:
    destination = Path(path)

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        mode = "w" if overwrite else "x"

        with destination.open(
            mode,
            encoding=encoding,
            newline="",
        ) as stream:
            table.to_csv(
                stream,
                sep=sep,
                index=False,
            )

    except Exception as exc:
        raise TableOperationError(
            f"Не удалось записать CSV: {destination}"
        ) from exc

    return destination


def require_columns(
    table: pd.DataFrame,
    columns: Iterable[str],
) -> None:
    missing = [
        column
        for column in columns
        if column not in table.columns
    ]

    if missing:
        raise TableOperationError(
            f"Отсутствуют колонки: {', '.join(missing)}"
        )


def filter_rows(
    table: pd.DataFrame,
    column: str,
    value: Any,
) -> pd.DataFrame:
    require_columns(table, [column])

    mask = (
        table[column].isna()
        if pd.isna(value)
        else table[column].eq(value)
    )

    return table.loc[mask].copy().reset_index(drop=True)


def merge_tables(
    tables: Iterable[pd.DataFrame],
) -> pd.DataFrame:
    items = list(tables)

    if not items:
        raise TableOperationError(
            "Нет таблиц для объединения"
        )

    expected_columns = items[0].columns

    if not expected_columns.is_unique:
        raise TableOperationError(
            "Названия колонок не должны повторяться"
        )

    for index, table in enumerate(items[1:], start=2):
        if not table.columns.equals(expected_columns):
            raise TableOperationError(
                f"Таблица {index}: состав или порядок колонок отличается"
            )

    return pd.concat(items, ignore_index=True)