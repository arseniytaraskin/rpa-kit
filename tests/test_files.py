import pytest
from rpa_kit.exceptions import FileOperationError
from rpa_kit.files import copy_file, ensure_directory, find_files, read_json, write_json


def test_ensure_directory(tmp_path):
    assert ensure_directory(tmp_path / "nested" / "data").is_dir()


def test_json_roundtrip(tmp_path):
    data = {"message": "Проверка", "count": 3}
    path = tmp_path / "nested" / "result.json"
    write_json(path, data)
    assert read_json(path) == data


def test_write_json_does_not_overwrite_by_default(tmp_path):
    path = tmp_path / "result.json"
    write_json(path, {"version": 1})
    with pytest.raises(FileOperationError):
        write_json(path, {"version": 2})
    assert read_json(path) == {"version": 1}


def test_missing_json_raises_error(tmp_path):
    with pytest.raises(FileOperationError):
        read_json(tmp_path / "missing.json")


def test_invalid_json_raises_error(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("{invalid", encoding="utf-8")
    with pytest.raises(FileOperationError):
        read_json(path)


def test_copy_file(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("Данные", encoding="utf-8")
    destination = copy_file(source, tmp_path / "backup" / "copy.txt")
    assert destination.read_text(encoding="utf-8") == "Данные"


def test_copy_does_not_overwrite_by_default(tmp_path):
    source = tmp_path / "source.txt"
    destination = tmp_path / "copy.txt"
    source.write_text("Новые данные", encoding="utf-8")
    destination.write_text("Старые данные", encoding="utf-8")
    with pytest.raises(FileOperationError):
        copy_file(source, destination)
    assert destination.read_text(encoding="utf-8") == "Старые данные"


def test_find_files_recursive(tmp_path):
    write_json(tmp_path / "first.json", {})
    write_json(tmp_path / "nested" / "second.json", {})
    (tmp_path / "note.txt").write_text("Текст", encoding="utf-8")
    assert len(find_files(tmp_path, "*.json", recursive=True)) == 2
