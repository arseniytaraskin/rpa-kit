# RPA Kit — первый этап

Самостоятельная Python-библиотека базовых операций. Требуется Python 3.10+.
Оркестратор не используется. Реализован только модуль files, не весь первый слой.

## Запуск в Windows / PowerShell

Распакуйте папку rpa-kit, например в C:\Projects\rpa-kit.
Откройте эту папку в VS Code и терминал в корне проекта.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe examples\files_demo.py
.\.venv\Scripts\python.exe -m pytest -q
```

Для первоначальной установки зависимостей нужен интернет.
Ctrl+Shift+P → Python: Select Interpreter → .venv\Scripts\python.exe.

## Результат

Пример создаст output/task.json и output/backup/task.json.
Повторный запуск примера перезаписывает только эти демонстрационные файлы.
Ожидается успешное выполнение 8 тестов.

## Состав

- src/rpa_kit/files.py: создание каталогов, чтение/запись JSON, поиск и копирование файлов.
- src/rpa_kit/exceptions.py: RpaError и FileOperationError.
- examples/files_demo.py: композиция базовых операций.
- tests/test_files.py: восемь тестов с временными каталогами.
- pyproject.toml: установка пакета и зависимостей разработки.

Функции по умолчанию запрещают перезапись; для разрешения передайте overwrite=True.
Запись и копирование не атомарны: при сбое возможен частичный файл.
Защита от параллельного изменения файлов другими процессами не реализована.
HTTP, web, tables и слой конкретных приложений добавляются на следующих этапах.
