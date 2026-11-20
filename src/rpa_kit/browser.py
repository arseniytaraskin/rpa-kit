import math
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

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

    def current_url(self) -> str:
        driver = self._require_driver()

        with self._operation("Не удалось получить URL"):
            return driver.current_url

    def title(self) -> str:
        driver = self._require_driver()

        with self._operation("Не удалось получить заголовок"):
            return driver.title

    def refresh(self) -> None:
        driver = self._require_driver()

        with self._operation("Не удалось обновить страницу"):
            driver.refresh()

    def go_back(self) -> None:
        driver = self._require_driver()

        with self._operation("Не удалось вернуться назад"):
            driver.back()

    def go_forward(self) -> None:
        driver = self._require_driver()

        with self._operation("Не удалось перейти вперед"):
            driver.forward()

    def execute_script(self, script: str, *args: object) -> object:
        driver = self._require_driver()

        if not isinstance(script, str) or not script.strip():
            raise ValueError("Скрипт должен быть непустой строкой")

        with self._operation("Не удалось выполнить JavaScript"):
            return driver.execute_script(script, *args)

    def find_element(
        self,
        selector: str,
        *,
        by: str = By.CSS_SELECTOR,
        timeout: float | None = None,
    ):
        driver = self._require_driver()

        if timeout is not None and (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("timeout должен быть положительным числом")

        with self._operation("Не удалось найти элемент"):
            return WebDriverWait(
                driver,
                self._timeout if timeout is None else timeout,
            ).until(
                EC.presence_of_element_located((by, selector))
            )

    def find_elements(
        self,
        selector: str,
        *,
        by: str = By.CSS_SELECTOR,
    ) -> list:
        driver = self._require_driver()

        with self._operation("Не удалось найти элементы"):
            return driver.find_elements(by, selector)

    def _wait(
        self,
        selector: str,
        by: str,
        *,
        clickable: bool,
        timeout: float | None = None,
    ):
        driver = self._require_driver()

        if timeout is not None and (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("timeout должен быть положительным числом")

        locator = (by, selector)

        condition = (
            EC.element_to_be_clickable(locator)
            if clickable
            else EC.visibility_of_element_located(locator)
        )

        return WebDriverWait(
            driver,
            self._timeout if timeout is None else timeout,
        ).until(condition)

    def click(
        self,
        selector: str,
        *,
        by: str = By.CSS_SELECTOR,
        timeout: float | None = None,
    ) -> None:
        with self._operation("Не удалось нажать на элемент"):
            element = self._wait(
                selector,
                by,
                clickable=True,
                timeout=timeout,
            )
            element.click()

    def fill(
        self,
        selector: str,
        value: str,
        *,
        by: str = By.CSS_SELECTOR,
        timeout: float | None = None,
    ) -> None:
        if not isinstance(value, str):
            value = str(value)

        with self._operation("Не удалось заполнить поле"):
            element = self._wait(
                selector,
                by,
                clickable=True,
                timeout=timeout,
            )
            element.clear()
            element.send_keys(value)

    def get_text(
        self,
        selector: str,
        *,
        by: str = By.CSS_SELECTOR,
        timeout: float | None = None,
    ) -> str:
        with self._operation("Не удалось получить текст"):
            element = self._wait(
                selector,
                by,
                clickable=False,
                timeout=timeout,
            )
            return element.text

    def get_attribute(
        self,
        selector: str,
        attribute: str,
        *,
        by: str = By.CSS_SELECTOR,
        timeout: float | None = None,
    ) -> str | None:
        if not isinstance(attribute, str) or not attribute:
            raise ValueError("Укажите имя атрибута")

        with self._operation("Не удалось получить атрибут"):
            element = self._wait(
                selector,
                by,
                clickable=False,
                timeout=timeout,
            )
            return element.get_attribute(attribute)

    def is_visible(
        self,
        selector: str,
        *,
        by: str = By.CSS_SELECTOR,
        timeout: float | None = None,
    ) -> bool:
        driver = self._require_driver()

        if timeout is not None and (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("timeout должен быть положительным числом")

        try:
            self._wait(
                selector,
                by,
                clickable=False,
                timeout=timeout,
            )
        except BrowserTimeoutError:
            return False

        return True

    def wait_visible(
        self,
        selector: str,
        *,
        by: str = By.CSS_SELECTOR,
        timeout: float | None = None,
    ) -> None:
        self._wait(
            selector,
            by,
            clickable=False,
            timeout=timeout,
        )

    def wait_hidden(
        self,
        selector: str,
        *,
        by: str = By.CSS_SELECTOR,
        timeout: float | None = None,
    ) -> None:
        driver = self._require_driver()

        if timeout is not None and (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("timeout должен быть положительным числом")

        with self._operation("Не удалось дождаться исчезновения элемента"):
            WebDriverWait(
                driver,
                self._timeout if timeout is None else timeout,
            ).until(
                EC.invisibility_of_element_located(
                    (by, selector)
                )
            )

    def wait_text(
        self,
        selector: str,
        text: str,
        *,
        by: str = By.CSS_SELECTOR,
        timeout: float | None = None,
    ) -> None:
        driver = self._require_driver()

        if timeout is not None and (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("timeout должен быть положительным числом")

        with self._operation("Не удалось дождаться текста"):
            WebDriverWait(
                driver,
                self._timeout if timeout is None else timeout,
            ).until(
                EC.text_to_be_present_in_element(
                    (by, selector),
                    text,
                )
            )

    def select_option(
        self,
        selector: str,
        value: str,
        *,
        by: str = By.CSS_SELECTOR,
        timeout: float | None = None,
    ) -> None:
        with self._operation("Не удалось выбрать значение"):
            element = self._wait(
                selector,
                by,
                clickable=True,
                timeout=timeout,
            )

            select = Select(element)

            try:
                select.select_by_value(value)
            except NoSuchElementException:
                select.select_by_visible_text(value)

    def select_option_by_index(
        self,
        selector: str,
        index: int,
        *,
        by: str = By.CSS_SELECTOR,
        timeout: float | None = None,
    ) -> None:
        if not isinstance(index, int) or isinstance(index, bool):
            raise ValueError("Укажите целочисленный индекс")

        with self._operation("Не удалось выбрать значение по индексу"):
            element = self._wait(
                selector,
                by,
                clickable=True,
                timeout=timeout,
            )

            Select(element).select_by_index(index)

    def set_checkbox(
        self,
        selector: str,
        checked: bool,
        *,
        by: str = By.CSS_SELECTOR,
        timeout: float | None = None,
    ) -> None:
        if not isinstance(checked, bool):
            raise ValueError("checked должен быть bool")

        with self._operation("Не удалось изменить чекбокс"):
            element = self._wait(
                selector,
                by,
                clickable=True,
                timeout=timeout,
            )

            if element.is_selected() != checked:
                element.click()

    def screenshot(
        self,
        path: str | Path,
        *,
        full_page: bool = False,
    ) -> Path:
        driver = self._require_driver()
        destination = Path(path)

        if destination.suffix.lower() != ".png":
            raise ValueError(
                "Скриншот должен иметь расширение .png"
            )

        with self._operation("Не удалось сохранить скриншот"):
            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            if full_page:
                original_size = driver.get_window_size()
                original_position = driver.get_window_position()

                try:
                    driver.set_window_size(
                        1920,
                        1080,
                    )
                    driver.execute_script(
                        "window.scrollTo(0, 0);"
                    )

                    if not driver.save_screenshot(
                        str(destination.resolve())
                    ):
                        raise BrowserError(
                            "Браузер не сохранил скриншот"
                        )

                    return destination
                finally:
                    driver.set_window_size(
                        original_size["width"],
                        original_size["height"],
                    )
                    driver.set_window_position(
                        original_position["x"],
                        original_position["y"],
                    )

            if not driver.save_screenshot(
                str(destination.resolve())
            ):
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