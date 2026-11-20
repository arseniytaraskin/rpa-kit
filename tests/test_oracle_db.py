from unittest.mock import MagicMock, patch

import oracledb
import pytest

from rpa_kit.exceptions import (
    OracleAuthenticationError,
    OracleConnectionError,
    OracleDatabaseError,
)
from rpa_kit.oracle_db import (
    OracleDatabase,
    validate_identifier,
)


@pytest.fixture
def database():
    return OracleDatabase(
        user="robot_user",
        password="secret",
        dsn="db.example.com:1521/ORCLPDB1",
    )


def test_validate_identifier():
    assert validate_identifier("TASKS") == "TASKS"


@pytest.mark.parametrize(
    "value",
    ["", "1table", "table name", "table-name"],
)
def test_invalid_identifier(value):
    with pytest.raises(ValueError):
        validate_identifier(value)


def test_invalid_settings():
    with pytest.raises(ValueError):
        OracleDatabase(
            user="",
            password="secret",
            dsn="db:1521/ORCL",
        )

    with pytest.raises(ValueError):
        OracleDatabase(
            user="robot",
            password="",
            dsn="db:1521/ORCL",
        )

    with pytest.raises(ValueError):
        OracleDatabase(
            user="robot",
            password="secret",
            dsn="",
        )


def test_connect_success(database):
    connection = MagicMock()

    with patch(
        "rpa_kit.oracle_db.oracledb.connect",
        return_value=connection,
    ):
        database.connect()

    assert database._connection is connection

    database.close()


def test_connect_authentication_error(database):
    error = MagicMock()
    error.is_a.return_value = True
    error.code = 1017

    failure = oracledb.Error(error)

    with patch(
        "rpa_kit.oracle_db.oracledb.connect",
        side_effect=failure,
    ):
        with pytest.raises(OracleAuthenticationError):
            database.connect()


def test_connect_network_error(database):
    with patch(
        "rpa_kit.oracle_db.oracledb.connect",
        side_effect=OSError,
    ):
        with pytest.raises(OracleConnectionError):
            database.connect()


def test_query(database):
    connection = MagicMock()
    cursor = MagicMock()

    cursor.description = [
        ("ID",),
        ("NAME",),
    ]
    cursor.fetchall.return_value = [
        (1, "Первый"),
        (2, "Второй"),
    ]

    connection.cursor.return_value = cursor
    database._connection = connection

    result = database.query(
        "SELECT id, name FROM tasks"
    )

    assert result == [
        {"ID": 1, "NAME": "Первый"},
        {"ID": 2, "NAME": "Второй"},
    ]

    cursor.close.assert_called_once()


def test_query_one(database):
    connection = MagicMock()
    cursor = MagicMock()

    cursor.description = [("COUNT",)]
    cursor.fetchone.return_value = (3,)

    connection.cursor.return_value = cursor
    database._connection = connection

    assert database.query_value(
        "SELECT COUNT(*) FROM tasks"
    ) == 3

    cursor.close.assert_called_once()


def test_query_without_connection(database):
    with pytest.raises(OracleDatabaseError):
        database.query("SELECT 1 FROM DUAL")


def test_insert_builds_named_parameters(database):
    connection = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = 1

    connection.cursor.return_value = cursor
    database._connection = connection

    affected = database.insert(
        "TASKS",
        {
            "TITLE": "Проверка",
            "STATUS": "NEW",
        },
    )

    sql = cursor.execute.call_args[0][0]

    assert affected == 1
    assert 'INSERT INTO "TASKS"' in sql
    assert ":TITLE" in sql
    assert ":STATUS" in sql
    cursor.close.assert_called_once()


def test_delete_requires_where(database):
    database._connection = MagicMock()

    with pytest.raises(ValueError):
        database.delete("TASKS", "")


def test_transaction_commit_and_rollback(database):
    connection = MagicMock()
    database._connection = connection

    with database.transaction():
        pass

    connection.commit.assert_called_once_with()

    with pytest.raises(ValueError):
        with database.transaction():
            raise ValueError("Ошибка")

    connection.rollback.assert_called_once_with()