from pathlib import Path
from rpa_kit.files import copy_file, find_files, read_json, write_json

PROJECT_DIR = Path(__file__).resolve().parents[1]


def main():
    output_dir = PROJECT_DIR / "output"
    source = write_json(
        output_dir / "task.json",
        {"ticket_id": "DEMO-001", "service": "exchange_rate",
         "params": {"base": "USD", "target": "EUR"}},
        overwrite=True,
    )
    task = read_json(source)
    backup = copy_file(source, output_dir / "backup" / "task.json", overwrite=True)
    json_files = find_files(output_dir, "*.json", recursive=True)
    print("Обращение:", task["ticket_id"])
    print("Копия:", backup)
    print("Найденные JSON:")
    for path in json_files:
        print(" -", path)


if __name__ == "__main__":
    main()
