from pathlib import Path

from rpa_kit.browser import Browser
from rpa_kit.exceptions import BrowserError


PROJECT_DIR = Path(__file__).resolve().parents[1]

HTML = """<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>RPA Kit Demo</title>
</head>
<body>
    <h1>Проверка browser</h1>
    <label for="name">Имя</label>
    <input id="name" type="text">
    <button id="submit" type="button">Отправить</button>
    <p id="result">Ожидание</p>

    <script>
        document.querySelector("#submit").addEventListener(
            "click",
            () => {
                const name = document.querySelector("#name").value;
                document.querySelector("#result").textContent =
                    "Привет, " + name + "!";
            }
        );
    </script>
</body>
</html>
"""


def main() -> int:
    output = PROJECT_DIR / "output" / "browser_demo"

    try:
        output.mkdir(parents=True, exist_ok=True)

        page = output / "form.html"
        page.write_text(HTML, encoding="utf-8")

        with Browser() as browser:
            browser.open(page.resolve().as_uri())
            browser.fill("#name", "Робот")
            browser.click("#submit")
            browser.wait_text("#result", "Привет, Робот!")

            result = browser.get_text("#result")
            screenshot = browser.screenshot(
                output / "result.png"
            )

        print(f"Результат: {result}")
        print(f"Скриншот: {screenshot}")

        return 0

    except (BrowserError, OSError) as exc:
        print(f"Ошибка: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())