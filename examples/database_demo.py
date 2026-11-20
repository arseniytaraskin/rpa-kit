from pathlib import Path

from rpa_kit.database import Database
from rpa_kit.exceptions import DatabaseError


PROJECT_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    database_path = (
        PROJECT_DIR / "output" / "database_demo.sqlite"
    )

    try:
        with Database(database_path) as database:
            database.create_table(
                "tasks",
                {
                    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                    "title": "TEXT NOT NULL",
                    "status": "TEXT NOT NULL DEFAULT 'new'",
                },
            )

            task_id = database.insert(
                "tasks",
                {
                    "title": "Проверить отчёт",
                    "status": "new",
                },
            )

            database.insert_many(
                "tasks",
                [
                    {
                        "title": "Отправить письмо",
                        "status": "pending",
                    },
                    {
                        "title": "Сформировать Excel",
                        "status": "done",
                    },
                ],
            )

            database.update(
                "tasks",
                {"status": "done"},
                "id = ?",
                (task_id,),
            )

            tasks = database.paginate(
                "tasks",
                page=1,
                page_size=10,
                order_by="id",
            )

            completed = database.count(
                "tasks",
                "status = ?",
                ("done",),
            )

            export_path = database.export_table(
                "tasks",
                PROJECT_DIR / "output" / "tasks.xlsx",
                format="xlsx",
            )

            print(f"Всего задач: {database.count('tasks')}")
            print(f"Завершённых: {completed}")
            print(f"Экспорт: {export_path}")

            for task in tasks:
                print(
                    f"{task['id']}: "
                    f"{task['title']} — {task['status']}"
                )

        return 0

    except DatabaseError as exc:
        print(f"Ошибка: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())