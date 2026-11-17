import json
import shutil
from pathlib import Path
from typing import Any

from rpa_kit.exceptions import FileOperationError


def ensure_directory(path: str | Path) -> Path:
    """Создает каталог, если его еще нет."""
    directory = Path(path)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FileOperationError(f"Не удалось создать каталог: {directory}") from exc
    return directory


def read_json(path: str | Path) -> Any:
    """Читает JSON-файл."""
    source = Path(path)
    try:
        return json.loads(source.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise FileOperationError(f"Не удалось прочитать JSON: {source}") from exc


def write_json(path: str | Path, data: Any, *, overwrite: bool = False) -> Path:
    """Записывает JSON. По умолчанию не заменяет существующий файл."""
    destination = Path(path)
    try:
        text = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
        ensure_directory(destination.parent)
        mode = "w" if overwrite else "x"
        with destination.open(mode, encoding="utf-8") as stream:
            stream.write(text)
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        raise FileOperationError(f"Не удалось записать JSON: {destination}") from exc
    return destination


def find_files(directory: str | Path, pattern: str = "*", *, recursive: bool = False) -> list[Path]:
    """Возвращает файлы, соответствующие шаблону."""
    root = Path(directory)
    try:
        if not root.is_dir():
            raise FileOperationError(f"Каталог не найден: {root}")
        matches = root.rglob(pattern) if recursive else root.glob(pattern)
        return sorted(path for path in matches if path.is_file())
    except OSError as exc:
        raise FileOperationError(f"Не удалось выполнить поиск в каталоге: {root}") from exc


def copy_file(source: str | Path, destination: str | Path, *, overwrite: bool = False) -> Path:
    """Копирует файл. destination — полный путь целевого файла."""
    source = Path(source)
    destination = Path(destination)
    try:
        if not source.is_file():
            raise FileOperationError(f"Исходный файл не найден: {source}")
        if source.resolve() == destination.resolve():
            raise FileOperationError("Исходный и целевой пути совпадают")
        ensure_directory(destination.parent)
        mode = "wb" if overwrite else "xb"
        with source.open("rb") as input_stream:
            with destination.open(mode) as output_stream:
                shutil.copyfileobj(input_stream, output_stream)
    except OSError as exc:
        raise FileOperationError(f"Не удалось скопировать {source} в {destination}") from exc
    return destination
