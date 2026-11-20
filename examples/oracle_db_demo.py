import os

from rpa_kit.exceptions import OracleDatabaseError
from rpa_kit.oracle_db import OracleDatabase


def main() -> int:
    user = os.getenv("ORACLE_USER")
    password = os.getenv("ORACLE_PASSWORD")
    dsn = os.getenv("ORACLE_DSN")

    if not all((user, password, dsn)):
        print(
            "Задайте переменные ORACLE_USER, "
            "ORACLE_PASSWORD и ORACLE_DSN"
        )
        return 1

    try:
        with OracleDatabase(
            user=user,
            password=password,
            dsn=dsn,
        ) as database:
            version = database.query_value(
                "SELECT banner FROM v$version "
                "WHERE ROWNUM = 1"
            )

            print(f"Oracle: {version}")

            result = database.query(
                """
                SELECT *
                FROM user_tables
                WHERE ROWNUM <= 10
                """
            )

            print(f"Найдено таблиц: {len(result)}")

        return 0

    except OracleDatabaseError as exc:
        print(f"Ошибка: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())