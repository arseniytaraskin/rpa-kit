import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from rpa_kit.exceptions import DatabaseError


class Database:
    def __init__(
        self,
        path: str | Path,
        *,
        timeout: float = 30,
    ):
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or timeout <= 0
        ):
            raise ValueError(
                "timeout должен быть положительным числом"
            )

        self.path = Path(path)
        self.timeout = timeout
        self._connection = None

    def _require_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise DatabaseError("Соединение с базой не открыто")

        return self._connection

    @contextmanager
    def _operation(self, message: str) -> Iterator[None]:
        try:
            yield
        except sqlite3.IntegrityError as exc:
            raise DatabaseError(
                f"{message}: нарушение ограничений базы"
            ) from exc
        except sqlite3.OperationalError as exc:
            raise DatabaseError(
                f"{message}: ошибка выполнения SQL"
            ) from exc
        except sqlite3.DatabaseError as exc:
            raise DatabaseError(message) from exc

    def connect(self) -> None:
        if self._connection is not None:
            raise DatabaseError("Соединение уже открыто")

        try:
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            connection = sqlite3.connect(
                self.path,
                timeout=self.timeout,
            )

            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")

            self._connection = connection

        except sqlite3.Error as exc:
            raise DatabaseError(
                f"Не удалось открыть базу: {self.path}"
            ) from exc

    def close(self) -> None:
        if self._connection is None:
            return

        connection = self._connection
        self._connection = None

        try:
            connection.close()
        except sqlite3.Error as exc:
            raise DatabaseError(
                "Не удалось закрыть соединение"
            ) from exc

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.close()
        else:
            try:
                self.close()
            except DatabaseError:
                pass

    def execute(
        self,
        sql: str,
        parameters: tuple | dict = (),
    ) -> sqlite3.Cursor:
        connection = self._require_connection()

        if not isinstance(sql, str) or not sql.strip():
            raise ValueError("Укажите SQL-запрос")

        with self._operation("Не удалось выполнить запрос"):
            return connection.execute(sql, parameters)

    def execute_many(
        self,
        sql: str,
        parameters: list[tuple | dict],
    ) -> int:
        connection = self._require_connection()

        if not isinstance(parameters, list):
            raise ValueError("parameters должен быть списком")

        with self._operation("Не удалось выполнить пакет запросов"):
            cursor = connection.executemany(
                sql,
                parameters,
            )
            connection.commit()

            return cursor.rowcount

    def query(
        self,
        sql: str,
        parameters: tuple | dict = (),
    ) -> list[sqlite3.Row]:
        cursor = self.execute(sql, parameters)

        return cursor.fetchall()

    def query_one(
        self,
        sql: str,
        parameters: tuple | dict = (),
    ) -> sqlite3.Row | None:
        cursor = self.execute(sql, parameters)

        return cursor.fetchone()

    def query_value(
        self,
        sql: str,
        parameters: tuple | dict = (),
        *,
        default: Any = None,
    ) -> Any:
        row = self.query_one(sql, parameters)

        if row is None or not len(row):
            return default

        return row[0]

    def transaction(self):
        connection = self._require_connection()

        return connection

    def create_table(
        self,
        table: str,
        columns: dict[str, str],
        *,
        if_not_exists: bool = True,
    ) -> None:
        if not table.isidentifier():
            raise ValueError("Некорректное имя таблицы")

        if not columns:
            raise ValueError("Укажите колонки таблицы")

        definitions = []

        for name, definition in columns.items():
            if not name.isidentifier():
                raise ValueError(
                    f"Некорректное имя колонки: {name}"
                )

            definitions.append(
                f"{name} {definition}"
            )

        exists = "IF NOT EXISTS " if if_not_exists else ""

        sql = (
            f"CREATE TABLE {exists}"
            f'"{table}" ('
            f"{', '.join(definitions)}"
            ")"
        )

        with self._operation("Не удалось создать таблицу"):
            self._require_connection().execute(sql)
            self._require_connection().commit()

    def table_exists(self, table: str) -> bool:
        if not table.isidentifier():
            raise ValueError("Некорректное имя таблицы")

        result = self.query_value(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            """,
            (table,),
            default=0,
        )

        return bool(result)

    def insert(
        self,
        table: str,
        values: dict[str, Any],
    ) -> int:
        if not values:
            raise ValueError("Нет значений для вставки")

        columns = list(values)
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(
            f'"{column}"' for column in columns
        )

        sql = (
            f'INSERT INTO "{table}" '
            f"({column_sql}) "
            f"VALUES ({placeholders})"
        )

        cursor = self.execute(
            sql,
            tuple(values.values()),
        )
        self._require_connection().commit()

        return cursor.lastrowid

    def insert_many(
        self,
        table: str,
        rows: list[dict[str, Any]],
    ) -> int:
        if not rows:
            return 0

        columns = list(rows[0])

        if any(
            set(row) != set(columns)
            for row in rows
        ):
            raise ValueError(
                "Все строки должны иметь одинаковые колонки"
            )

        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(
            f'"{column}"' for column in columns
        )

        sql = (
            f'INSERT INTO "{table}" '
            f"({column_sql}) "
            f"VALUES ({placeholders})"
        )

        parameters = [
            tuple(
                row[column]
                for column in columns
            )
            for row in rows
        ]

        return self.execute_many(sql, parameters)

    def update(
        self,
        table: str,
        values: dict[str, Any],
        where: str,
        parameters: tuple | dict = (),
    ) -> int:
        if not values:
            raise ValueError("Нет значений для обновления")

        if not where.strip():
            raise ValueError(
                "Укажите условие WHERE"
            )

        assignments = ", ".join(
            f'"{column}" = ?'
            for column in values
        )

        sql = (
            f'UPDATE "{table}" '
            f"SET {assignments} "
            f"WHERE {where}"
        )

        all_parameters = (
            tuple(values.values()) + parameters
            if isinstance(parameters, tuple)
            else parameters
        )

        cursor = self.execute(sql, all_parameters)
        self._require_connection().commit()

        return cursor.rowcount

    def delete(
        self,
        table: str,
        where: str,
        parameters: tuple | dict = (),
    ) -> int:
        if not where.strip():
            raise ValueError(
                "Укажите условие WHERE"
            )

        sql = f'DELETE FROM "{table}" WHERE {where}'

        cursor = self.execute(sql, parameters)
        self._require_connection().commit()

        return cursor.rowcount

    def count(
        self,
        table: str,
        where: str = "1 = 1",
        parameters: tuple | dict = (),
    ) -> int:
        sql = (
            f'SELECT COUNT(*) FROM "{table}" '
            f"WHERE {where}"
        )

        return int(
            self.query_value(
                sql,
                parameters,
                default=0,
            )
        )

    def exists(
        self,
        table: str,
        where: str,
        parameters: tuple | dict = (),
    ) -> bool:
        return self.count(
            table,
            where,
            parameters,
        ) > 0

    def paginate(
        self,
        table: str,
        *,
        page: int = 1,
        page_size: int = 50,
        where: str = "1 = 1",
        parameters: tuple | dict = (),
        order_by: str | None = None,
    ) -> list[sqlite3.Row]:
        if page < 1:
            raise ValueError("page должен быть не меньше 1")

        if page_size < 1:
            raise ValueError("page_size должен быть не меньше 1")

        offset = (page - 1) * page_size
        order = (
            f" ORDER BY {order_by}"
            if order_by
            else ""
        )

        sql = (
            f'SELECT * FROM "{table}" '
            f"WHERE {where}"
            f"{order} "
            f"LIMIT ? OFFSET ?"
        )

        if isinstance(parameters, tuple):
            parameters = parameters + (page_size, offset)
        else:
            parameters = {
                **parameters,
                "page_size": page_size,
                "offset": offset,
            }

        return self.query(sql, parameters)

    def upsert(
        self,
        table: str,
        values: dict[str, Any],
        *,
        conflict_columns: list[str],
    ) -> int:
        if not values:
            raise ValueError("Нет значений для вставки")

        if not conflict_columns:
            raise ValueError(
                "Укажите колонки конфликта"
            )

        columns = list(values)
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(
            f'"{column}"' for column in columns
        )
        conflict_sql = ", ".join(
            f'"{column}"' for column in conflict_columns
        )
        update_sql = ", ".join(
            f'"{column}" = excluded."{column}"'
            for column in columns
            if column not in conflict_columns
        )

        if not update_sql:
            raise ValueError(
                "Нет колонок для обновления"
            )

        sql = (
            f'INSERT INTO "{table}" '
            f"({column_sql}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT({conflict_sql}) "
            f"DO UPDATE SET {update_sql}"
        )

        cursor = self.execute(
            sql,
            tuple(values.values()),
        )
        self._require_connection().commit()

        return cursor.rowcount

    def export_table(
        self,
        table: str,
        path: str | Path,
        *,
        format: str = "xlsx",
        where: str = "1 = 1",
        parameters: tuple | dict = (),
    ) -> Path:
        from rpa_kit.tables import (
            read_csv,
            write_csv,
            write_excel,
        )

        if not table.isidentifier():
            raise ValueError("Некорректное имя таблицы")

        rows = self.query(
            f'SELECT * FROM "{table}" WHERE {where}',
            parameters,
        )

        columns = rows[0].keys() if rows else []
        data = [
            {
                column: row[column]
                for column in columns
            }
            for row in rows
        ]

        destination = Path(path)

        if format == "xlsx":
            import pandas as pd

            return write_excel(
                pd.DataFrame(data, columns=columns),
                destination,
                overwrite=True,
            )

        if format == "csv":
            import csv

            with destination.open(
                "w",
                encoding="utf-8-sig",
                newline="",
            ) as stream:
                writer = csv.DictWriter(
                    stream,
                    fieldnames=columns,
                )
                writer.writeheader()
                writer.writerows(data)

            return destination

        raise ValueError(
            "format должен быть xlsx или csv"
        )

    def vacuum(self) -> None:
        with self._operation("Не удалось выполнить VACUUM"):
            self._require_connection().execute("VACUUM")
            self._require_connection().commit()