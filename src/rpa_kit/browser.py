import math
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from rpa_kit.exceptions import BrowserError, BrowserTimeoutError


class Browser:
    def __init__(
        self,
        *,
        headless: bool = False,
        timeout: float = 15,
        page_load_timeout: float = 30,
    ):
        for name, value in (
            ("timeout", timeout),
            ("page_load_timeout", page_load_timeout),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError(
                    f"{name} должен быть положительным числом"
                )

        self._headless = headless
        self._timeout = timeout
        self._page_load_timeout = page_load_timeout
        self._driver = None

    @contextmanager
    def _operation(self, message: str) -> Iterator[None]:
        try:
            yield
        except TimeoutException as exc:
            raise BrowserTimeoutError(message) from exc
        except (WebDriverException, OSError) as exc:
            raise BrowserError(message) from exc

    def _require_driver(self):
        if self._driver is None:
            raise BrowserError("Браузер не запущен")

        return self._driver

    def start(self) -> None:
        if self._driver is not None:
            raise BrowserError("Браузер уже запущен")

        options = webdriver.ChromeOptions()

        if self._headless:
            options.add_argument("--headless=new")

        options.add_argument("--window-size=1440,900")

        with self._operation("Не удалось запустить Chrome"):
            driver = webdriver.Chrome(options=options)

            try:
                driver.set_page_load_timeout(
                    self._page_load_timeout
                )
            except WebDriverException:
                try:
                    driver.quit()
                except WebDriverException:
                    pass
                raise

            self._driver = driver

    def open(self, url: str) -> None:
        driver = self._require_driver()

        with self._operation("Не удалось открыть страницу"):
            driver.get(url)

    def _wait(self, selector: str, by: str, *, clickable: bool):
        driver = self._require_driver()
        locator = (by, selector)

        condition = (
            EC.element_to_be_clickable(locator)
            if clickable
            else EC.visibility_of_element_located(locator)
        )

        return WebDriverWait(
            driver,
            self._timeout,
        ).until(condition)

    def click(
        self,
        selector: str,
        *,
        by: str = By.CSS_SELECTOR,
    ) -> None:
        with self._operation("Не удалось нажать на элемент"):
            element = self._wait(selector, by, clickable=True)
            element.click()

    def fill(
        self,
        selector: str,
        value: str,
        *,
        by: str = By.CSS_SELECTOR,
    ) -> None:
        with self._operation("Не удалось заполнить поле"):
            element = self._wait(selector, by, clickable=True)
            element.clear()
            element.send_keys(value)

    def get_text(
        self,
        selector: str,
        *,
        by: str = By.CSS_SELECTOR,
    ) -> str:
        with self._operation("Не удалось получить текст"):
            element = self._wait(selector, by, clickable=False)
            return element.text

    def wait_text(
        self,
        selector: str,
        text: str,
        *,
        by: str = By.CSS_SELECTOR,
    ) -> None:
        driver = self._require_driver()

        with self._operation("Не удалось дождаться текста"):
            WebDriverWait(driver, self._timeout).until(
                EC.text_to_be_present_in_element(
                    (by, selector),
                    text,
                )
            )

    def screenshot(self, path: str | Path) -> Path:
        driver = self._require_driver()
        destination = Path(path)

        if destination.suffix.lower() != ".png":
            raise ValueError("Скриншот должен иметь расширение .png")

        with self._operation("Не удалось сохранить скриншот"):
            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            if not driver.save_screenshot(str(destination.resolve())):
                raise BrowserError(
                    "Браузер не сохранил скриншот"
                )

        return destination

    def close(self) -> None:
        if self._driver is None:
            return

        driver = self._driver
        self._driver = None

        with self._operation("Не удалось закрыть браузер"):
            driver.quit()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.close()
        else:
            try:
                self.close()
            except BrowserError:
                pass