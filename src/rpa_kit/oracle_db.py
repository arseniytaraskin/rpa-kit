import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import oracledb

from rpa_kit.exceptions import (
    OracleAuthenticationError,
    OracleConnectionError,
    OracleDatabaseError,
)


IDENTIFIER_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_$#]*$"
)


def validate_identifier(value: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(
            f"Некорректный идентификатор Oracle: {value}"
        )

    return value


class OracleDatabase:
    def __init__(
        self,
        *,
        user: str,
        password: str,
        dsn: str,
        timeout: float = 30,
        fetch_size: int = 500,
    ):
        if not user.strip():
            raise ValueError("Укажите пользователя Oracle")

        if not password:
            raise ValueError("Укажите пароль Oracle")

        if not dsn.strip():
            raise ValueError(
                "Укажите DSN, например host:port/service_name"
            )

        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or timeout <= 0
        ):
            raise ValueError("timeout должен быть положительным числом")

        if (
            not isinstance(fetch_size, int)
            or isinstance(fetch_size, bool)
            or fetch_size < 1
        ):
            raise ValueError("fetch_size должен быть целым числом не меньше 1")

        self.user = user.strip()
        self.password = password
        self.dsn = dsn.strip()
        self.timeout = timeout
        self.fetch_size = fetch_size
        self._connection = None

    def _require_connection(self) -> oracledb.Connection:
        if self._connection is None:
            raise OracleDatabaseError(
                "Соединение с Oracle не открыто"
            )

        return self._connection

    @contextmanager
    def _operation(self, message: str) -> Iterator[None]:
        try:
            yield
        except oracledb.IntegrityError as exc:
            raise OracleDatabaseError(
                f"{message}: нарушение ограничений базы"
            ) from exc
        except oracledb.DatabaseError as exc:
            error = exc.args[0] if exc.args else None

            if getattr(error, "is_a", None) and error.is_a(
                oracledb.error
            ):
                code = getattr(error, "code", None)

                if code in (1017, 28000):
                    raise OracleAuthenticationError(
                        "Не удалось авторизоваться в Oracle"
                    ) from exc

            raise OracleDatabaseError(
                f"{message}: {exc}"
            ) from exc
        except OSError as exc:
            raise OracleConnectionError(
                f"{message}: сетевая ошибка"
            ) from exc

    def connect(self) -> None:
        if self._connection is not None:
            raise OracleDatabaseError(
                "Соединение уже открыто"
            )

        try:
            self._connection = oracledb.connect(
                user=self.user,
                password=self.password,
                dsn=self.dsn,
            )

        except oracledb.Error as exc:
            error = exc.args[0] if exc.args else None

            if getattr(error, "is_a", None) and error.is_a(
                oracledb.error
            ):
                code = getattr(error, "code", None)

                if code in (1017, 28000):
                    raise OracleAuthenticationError(
                        "Не удалось авторизоваться в Oracle"
                    ) from exc

            raise OracleConnectionError(
                f"Не удалось подключиться к Oracle: {self.dsn}"
            ) from exc

        except OSError as exc:
            raise OracleConnectionError(
                f"Не удалось подключиться к Oracle: {self.dsn}"
            ) from exc

    def close(self) -> None:
        if self._connection is None:
            return

        connection = self._connection
        self._connection = None

        try:
            connection.close()
        except oracledb.Error as exc:
            raise OracleDatabaseError(
                "Не удалось закрыть соединение с Oracle"
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
            except OracleDatabaseError:
                pass

    def execute(
        self,
        sql: str,
        parameters: dict[str, Any] | list | tuple = (),
    ) -> oracledb.Cursor:
        connection = self._require_connection()

        if not isinstance(sql, str) or not sql.strip():
            raise ValueError("Укажите SQL-запрос")

        with self._operation("Не удалось выполнить SQL"):
            cursor = connection.cursor()
            cursor.execute(sql, parameters)

            return cursor

    def query(
        self,
        sql: str,
        parameters: dict[str, Any] | list | tuple = (),
    ) -> list[dict[str, Any]]:
        cursor = self.execute(sql, parameters)

        try:
            columns = [
                column[0]
                for column in cursor.description
            ]

            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

        finally:
            cursor.close()

    def query_one(
        self,
        sql: str,
        parameters: dict[str, Any] | list | tuple = (),
    ) -> dict[str, Any] | None:
        cursor = self.execute(sql, parameters)

        try:
            columns = [
                column[0]
                for column in cursor.description
            ]

            row = cursor.fetchone()

            if row is None:
                return None

            return dict(zip(columns, row))

        finally:
            cursor.close()

    def query_value(
        self,
        sql: str,
        parameters: dict[str, Any] | list | tuple = (),
        *,
        default: Any = None,
    ) -> Any:
        row = self.query_one(sql, parameters)

        if not row:
            return default

        return next(iter(row.values()))

    def execute_non_query(
        self,
        sql: str,
        parameters: dict[str, Any] | list | tuple = (),
    ) -> int:
        cursor = self.execute(sql, parameters)

        try:
            return cursor.rowcount
        finally:
            cursor.close()

    def commit(self) -> None:
        with self._operation("Не удалось зафиксировать транзакцию"):
            self._require_connection().commit()

    def rollback(self) -> None:
        with self._operation("Не удалось отменить транзакцию"):
            self._require_connection().rollback()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self._require_connection()

        try:
            yield
            self.commit()
        except Exception:
            self.rollback()
            raise

    def insert(
        self,
        table: str,
        values: dict[str, Any],
        *,
        commit: bool = True,
    ) -> int:
        if not values:
            raise ValueError("Нет значений для вставки")

        table = validate_identifier(table)

        columns = list(values)
        column_sql = ", ".join(
            f'"{column}"' for column in columns
        )
        placeholders = ", ".join(
            f":{column}" for column in columns
        )

        sql = (
            f'INSERT INTO "{table}" '
            f"({column_sql}) "
            f"VALUES ({placeholders})"
        )

        affected = self.execute_non_query(
            sql,
            values,
        )

        if commit:
            self.commit()

        return affected

    def insert_many(
        self,
        table: str,
        rows: list[dict[str, Any]],
        *,
        commit: bool = True,
    ) -> int:
        if not rows:
            return 0

        table = validate_identifier(table)
        columns = list(rows[0])

        if any(
            set(row) != set(columns)
            for row in rows
        ):
            raise ValueError(
                "Все строки должны иметь одинаковые колонки"
            )

        column_sql = ", ".join(
            f'"{column}"' for column in columns
        )
        placeholders = ", ".join(
            f":{column}" for column in columns
        )

        sql = (
            f'INSERT INTO "{table}" '
            f"({column_sql}) "
            f"VALUES ({placeholders})"
        )

        with self._operation("Не удалось вставить строки"):
            connection = self._require_connection()

            with connection.cursor() as cursor:
                cursor.executemany(
                    sql,
                    rows,
                )
                affected = cursor.rowcount

        if commit:
            self.commit()

        return affected

    def update(
        self,
        table: str,
        values: dict[str, Any],
        where: str,
        parameters: dict[str, Any] | list | tuple = (),
        *,
        commit: bool = True,
    ) -> int:
        if not values:
            raise ValueError("Нет значений для обновления")

        if not where.strip():
            raise ValueError("Укажите условие WHERE")

        table = validate_identifier(table)

        assignments = ", ".join(
            f'"{column}" = :{column}'
            for column in values
        )

        sql = (
            f'UPDATE "{table}" '
            f"SET {assignments} "
            f"WHERE {where}"
        )

        if isinstance(parameters, dict):
            all_parameters = {
                **values,
                **parameters,
            }
        else:
            all_parameters = [
                *values.values(),
                *parameters,
            ]

        affected = self.execute_non_query(
            sql,
            all_parameters,
        )

        if commit:
            self.commit()

        return affected

    def delete(
        self,
        table: str,
        where: str,
        parameters: dict[str, Any] | list | tuple = (),
        *,
        commit: bool = True,
    ) -> int:
        if not where.strip():
            raise ValueError("Укажите условие WHERE")

        table = validate_identifier(table)

        sql = f'DELETE FROM "{table}" WHERE {where}'

        affected = self.execute_non_query(
            sql,
            parameters,
        )

        if commit:
            self.commit()

        return affected

    def call_procedure(
        self,
        name: str,
        parameters: dict[str, Any] | list | tuple = (),
        *,
        commit: bool = True,
    ) -> None:
        name = validate_identifier(name)

        if isinstance(parameters, dict):
            placeholders = ", ".join(
                f":{key}" for key in parameters
            )
        else:
            placeholders = ", ".join(
                ":" for _ in parameters
            )

        sql = (
            f"BEGIN {name}({placeholders}); END;"
        )

        with self._operation("Не удалось вызвать процедуру"):
            cursor = self.execute(sql, parameters)
            cursor.close()

        if commit:
            self.commit()

    def export_query(
        self,
        sql: str,
        path: str | Path,
        *,
        parameters: dict[str, Any] | list | tuple = (),
        format: str = "xlsx",
    ) -> Path:
        import pandas as pd

        from rpa_kit.tables import write_csv, write_excel

        rows = self.query(sql, parameters)
        table = pd.DataFrame(rows)

        destination = Path(path)

        if format == "xlsx":
            return write_excel(
                table,
                destination,
                overwrite=True,
            )

        if format == "csv":
            return write_csv(
                table,
                destination,
                overwrite=True,
            )

        raise ValueError(
            "format должен быть xlsx или csv"
        )