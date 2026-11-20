from unittest.mock import Mock, patch

import pytest
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
)

from rpa_kit.browser import Browser
from rpa_kit.exceptions import BrowserError, BrowserTimeoutError


@pytest.fixture
def browser_env():
    with patch(
        "rpa_kit.browser.webdriver.Chrome"
    ) as chrome, patch(
        "rpa_kit.browser.WebDriverWait"
    ) as wait_class:
        driver = chrome.return_value
        wait = wait_class.return_value
        browser = Browser()

        browser.start()

        try:
            yield browser, driver, wait
        finally:
            browser.close()


def test_start(browser_env):
    _, driver, _ = browser_env

    driver.set_page_load_timeout.assert_called_once_with(30)


def test_open(browser_env):
    browser, driver, _ = browser_env

    browser.open("https://example.org")

    driver.get.assert_called_once_with("https://example.org")


def test_fill(browser_env):
    browser, _, wait = browser_env
    element = wait.until.return_value

    browser.fill("#name", "Робот")

    element.clear.assert_called_once_with()
    element.send_keys.assert_called_once_with("Робот")


def test_click(browser_env):
    browser, _, wait = browser_env

    browser.click("#submit")

    wait.until.return_value.click.assert_called_once_with()


def test_get_text(browser_env):
    browser, _, wait = browser_env
    wait.until.return_value.text = "Готово"

    assert browser.get_text("#result") == "Готово"


def test_wait_text(browser_env):
    browser, _, wait = browser_env
    wait.until.return_value = True

    browser.wait_text("#result", "Готово")

    wait.until.assert_called_once()


def test_timeout(browser_env):
    browser, _, wait = browser_env
    wait.until.side_effect = TimeoutException()

    with pytest.raises(BrowserTimeoutError):
        browser.click("#missing")


def test_screenshot(browser_env, tmp_path):
    browser, driver, _ = browser_env
    path = tmp_path / "screens" / "result.png"

    assert browser.screenshot(path) == path
    assert path.parent.is_dir()

    driver.save_screenshot.assert_called_once_with(
        str(path.resolve())
    )


def test_screenshot_failure(browser_env, tmp_path):
    browser, driver, _ = browser_env
    driver.save_screenshot.return_value = False

    with pytest.raises(BrowserError):
        browser.screenshot(tmp_path / "result.png")


def test_close_is_idempotent(browser_env):
    browser, driver, _ = browser_env

    browser.close()
    browser.close()

    driver.quit.assert_called_once_with()


def test_not_started():
    browser = Browser()

    with pytest.raises(BrowserError):
        browser.open("https://example.org")


def test_invalid_timeout():
    with pytest.raises(ValueError):
        Browser(timeout=0)


def test_start_failure():
    with patch(
        "rpa_kit.browser.webdriver.Chrome",
        side_effect=WebDriverException(),
    ):
        with pytest.raises(BrowserError):
            Browser().start()


def test_context_manager_closes_browser():
    driver = Mock()

    with patch(
        "rpa_kit.browser.webdriver.Chrome",
        return_value=driver,
    ):
        with Browser():
            pass

    driver.quit.assert_called_once_with()