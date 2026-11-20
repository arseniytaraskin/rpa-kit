import sqlite3

import pytest

from rpa_kit.database import Database
from rpa_kit.exceptions import DatabaseError


@pytest.fixture
def database(tmp_path):
    database = Database(tmp_path / "test.sqlite")

    database.connect()

    try:
        yield database
    finally:
        database.close()


def test_connect_and_close(tmp_path):
    database = Database(tmp_path / "test.sqlite")

    database.connect()
    database.close()

    with pytest.raises(DatabaseError):
        database.query("SELECT 1")


def test_create_table(database):
    database.create_table(
        "items",
        {
            "id": "INTEGER PRIMARY KEY",
            "name": "TEXT",
        },
    )

    assert database.table_exists("items")


def test_insert_and_query(database):
    database.create_table(
        "items",
        {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT",
        },
    )

    item_id = database.insert(
        "items",
        {"name": "Первый"},
    )

    row = database.query_one(
        "SELECT * FROM items WHERE id = ?",
        (item_id,),
    )

    assert row["name"] == "Первый"


def test_insert_many(database):
    database.create_table(
        "items",
        {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT",
        },
    )

    inserted = database.insert_many(
        "items",
        [
            {"name": "A"},
            {"name": "B"},
        ],
    )

    assert inserted == 2
    assert database.count("items") == 2


def test_update(database):
    database.create_table(
        "items",
        {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT",
            "status": "TEXT",
        },
    )

    item_id = database.insert(
        "items",
        {
            "name": "Задача",
            "status": "new",
        },
    )

    updated = database.update(
        "items",
        {"status": "done"},
        "id = ?",
        (item_id,),
    )

    assert updated == 1

    row = database.query_one(
        "SELECT status FROM items WHERE id = ?",
        (item_id,),
    )

    assert row["status"] == "done"


def test_delete(database):
    database.create_table(
        "items",
        {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT",
        },
    )

    item_id = database.insert(
        "items",
        {"name": "Удалить"},
    )

    deleted = database.delete(
        "items",
        "id = ?",
        (item_id,),
    )

    assert deleted == 1
    assert not database.exists(
        "items",
        "id = ?",
        (item_id,),
    )


def test_paginate(database):
    database.create_table(
        "items",
        {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT",
        },
    )

    database.insert_many(
        "items",
        [
            {"name": f"Элемент {number}"}
            for number in range(1, 6)
        ],
    )

    first_page = database.paginate(
        "items",
        page=1,
        page_size=2,
        order_by="id",
    )

    second_page = database.paginate(
        "items",
        page=2,
        page_size=2,
        order_by="id",
    )

    assert len(first_page) == 2
    assert len(second_page) == 2
    assert first_page[0]["id"] == 1
    assert second_page[0]["id"] == 3


def test_upsert(database):
    database.create_table(
        "items",
        {
            "code": "TEXT PRIMARY KEY",
            "name": "TEXT",
        },
    )

    database.upsert(
        "items",
        {
            "code": "A1",
            "name": "Первый",
        },
        conflict_columns=["code"],
    )

    database.upsert(
        "items",
        {
            "code": "A1",
            "name": "Обновлённый",
        },
        conflict_columns=["code"],
    )

    row = database.query_one(
        "SELECT name FROM items WHERE code = ?",
        ("A1",),
    )

    assert row["name"] == "Обновлённый"


def test_delete_requires_where(database):
    with pytest.raises(ValueError):
        database.delete("items", "")


def test_export_csv(database, tmp_path):
    database.create_table(
        "items",
        {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT",
        },
    )

    database.insert(
        "items",
        {"name": "Экспорт"},
    )

    path = database.export_table(
        "items",
        tmp_path / "items.csv",
        format="csv",
    )

    assert path.is_file()


def test_export_invalid_format(database, tmp_path):
    with pytest.raises(ValueError):
        database.export_table(
            "items",
            tmp_path / "items.txt",
            format="txt",
        )


def test_transaction_rollback(database):
    database.create_table(
        "items",
        {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT NOT NULL",
        },
    )

    connection = database.transaction()

    try:
        connection.execute(
            'INSERT INTO items (name) VALUES (?)',
            ("Первая",),
        )
        connection.execute(
            'INSERT INTO items (name) VALUES (?)',
            (None,),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()

    assert database.count("items") == 0