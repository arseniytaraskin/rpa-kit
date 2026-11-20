import pandas as pd
import pytest

from rpa_kit.exceptions import TableOperationError
from rpa_kit.tables import (
    filter_rows,
    merge_tables,
    read_csv,
    read_excel,
    require_columns,
    write_csv,
    write_excel,
)


def test_excel_roundtrip(tmp_path):
    table = pd.DataFrame({
        "id": [1, 2],
        "name": ["Первый", "Второй"],
    })

    path = write_excel(table, tmp_path / "data.xlsx")
    result = read_excel(path)

    pd.testing.assert_frame_equal(result, table)


def test_csv_roundtrip(tmp_path):
    table = pd.DataFrame({
        "id": [1, 2],
        "name": ["Первый", "Второй"],
    })

    path = write_csv(table, tmp_path / "data.csv")
    result = read_csv(path)

    pd.testing.assert_frame_equal(result, table)


def test_require_columns():
    table = pd.DataFrame({"id": [1]})

    with pytest.raises(TableOperationError):
        require_columns(table, ["id", "status"])


def test_filter_rows():
    table = pd.DataFrame({
        "id": [1, 2, 3],
        "status": ["done", "pending", "done"],
    })

    result = filter_rows(table, "status", "done")

    assert result["id"].tolist() == [1, 3]
    assert len(table) == 3


def test_merge_tables():
    first = pd.DataFrame({"id": [1, 2]})
    second = pd.DataFrame({"id": [3]})

    result = merge_tables([first, second])

    assert result["id"].tolist() == [1, 2, 3]


def test_merge_rejects_different_columns():
    first = pd.DataFrame({"id": [1]})
    second = pd.DataFrame({"number": [2]})

    with pytest.raises(TableOperationError):
        merge_tables([first, second])


def test_merge_rejects_empty_list():
    with pytest.raises(TableOperationError):
        merge_tables([])


def test_excel_does_not_overwrite(tmp_path):
    path = tmp_path / "data.xlsx"

    write_excel(pd.DataFrame({"id": [1]}), path)

    with pytest.raises(TableOperationError):
        write_excel(pd.DataFrame({"id": [2]}), path)

    assert read_excel(path)["id"].tolist() == [1]


def test_csv_does_not_overwrite(tmp_path):
    path = tmp_path / "data.csv"

    write_csv(pd.DataFrame({"id": [1]}), path)

    with pytest.raises(TableOperationError):
        write_csv(pd.DataFrame({"id": [2]}), path)

    assert read_csv(path)["id"].tolist() == [1]


def test_missing_file(tmp_path):
    with pytest.raises(TableOperationError):
        read_excel(tmp_path / "missing.xlsx")