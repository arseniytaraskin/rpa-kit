import math
from typing import Any, Mapping
from urllib.parse import urlsplit

import requests

from rpa_kit.exceptions import (
    ApiError,
    ApiTimeoutError,
    ApiStatusError,
    ApiResponseError,
)


class ApiClient:
    """HTTP-клиент для последовательного выполнения операций.

    Автоматические повторы отключены.
    Проверка сертификатов TLS включена.
    """

    def __init__(
        self,
        *,
        timeout: tuple[float, float] = (5, 20),
        headers: Mapping[str, str] | None = None,
    ):
        if (
            not isinstance(timeout, tuple)
            or len(timeout) != 2
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
                for value in timeout
            )
        ):
            raise ValueError(
                "timeout должен быть парой положительных чисел"
            )

        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "rpa-kit/0.1",
        })

        if headers:
            self._session.headers.update(headers)

        self._closed = False

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        json: Any = None,
        data: Any = None,
        auth: Any = None,
        allow_redirects: bool = False,
    ) -> requests.Response:
        """Выполняет запрос и возвращает Response.

        Ответ необходимо закрыть после использования.
        HTTP 4xx/5xx преобразуются в ApiStatusError.
        """

        if self._closed:
            raise ApiError("Клиент уже закрыт")

        parsed = urlsplit(url)

        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
        ):
            raise ValueError("Требуется полный HTTP(S) URL")

        if json is not None and data is not None:
            raise ValueError("Передайте либо json, либо data")

        try:
            response = self._session.request(
                method=method.upper(),
                url=url,
                params=params,
                headers=headers,
                json=json,
                data=data,
                auth=auth,
                timeout=self.timeout,
                allow_redirects=allow_redirects,
            )

            try:
                response.raise_for_status()
            except requests.HTTPError:
                status_code = response.status_code
                response.close()
                raise ApiStatusError(status_code) from None

            return response

        except requests.Timeout:
            raise ApiTimeoutError(
                "Истек таймаут HTTP-запроса"
            ) from None

        except requests.RequestException:
            raise ApiError(
                "Не удалось выполнить HTTP-запрос"
            ) from None

    def request_json(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> Any:
        """Выполняет запрос, ожидая HTTP 2xx и JSON."""

        response = self.request(method, url, **kwargs)

        try:
            if not 200 <= response.status_code < 300:
                raise ApiResponseError(
                    "Для JSON-операции ожидался HTTP 2xx"
                )

            try:
                return response.json()
            except ValueError:
                raise ApiResponseError(
                    "Ответ не содержит корректный JSON"
                ) from None

        finally:
            response.close()

    def get_json(self, url: str, **kwargs: Any) -> Any:
        """Отправляет GET и возвращает JSON."""
        return self.request_json("GET", url, **kwargs)

    def post_json(
        self,
        url: str,
        *,
        json: Any,
        **kwargs: Any,
    ) -> Any:
        """Отправляет POST с JSON и возвращает JSON."""
        return self.request_json(
            "POST",
            url,
            json=json,
            **kwargs,
        )

    def close(self) -> None:
        """Закрывает HTTP-сессию."""
        if not self._closed:
            self._session.close()
            self._closed = True

    def __enter__(self):
        if self._closed:
            raise ApiError("Клиент уже закрыт")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()