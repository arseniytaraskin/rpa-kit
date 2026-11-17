from unittest.mock import patch

import pytest
import requests

from rpa_kit.api_client import ApiClient
from rpa_kit.exceptions import (
    ApiError,
    ApiTimeoutError,
    ApiStatusError,
    ApiResponseError,
)


def make_response(status=200, body=b'{"ok": true}'):
    response = requests.Response()
    response.status_code = status
    response._content = body
    response.encoding = "utf-8"
    return response


def test_get_json():
    with ApiClient() as client:
        with patch.object(
            client._session,
            "request",
            return_value=make_response(),
        ) as mock:
            result = client.get_json(
                "https://example.org",
                params={"id": 1},
            )

            assert result == {"ok": True}
            assert mock.call_args.kwargs["timeout"] == (5, 20)
            assert mock.call_args.kwargs["params"] == {"id": 1}
            assert mock.call_args.kwargs["allow_redirects"] is False


def test_post_json():
    with ApiClient() as client:
        with patch.object(
            client._session,
            "request",
            return_value=make_response(),
        ) as mock:
            client.post_json(
                "https://example.org",
                json={"name": "test"},
            )

            assert mock.call_args.kwargs["method"] == "POST"
            assert mock.call_args.kwargs["json"] == {"name": "test"}


def test_status_error():
    with ApiClient() as client:
        with patch.object(
            client._session,
            "request",
            return_value=make_response(404),
        ):
            with pytest.raises(ApiStatusError) as error:
                client.get_json("https://example.org")

            assert error.value.status_code == 404


def test_timeout_without_retry():
    with ApiClient() as client:
        with patch.object(
            client._session,
            "request",
            side_effect=requests.Timeout,
        ) as mock:
            with pytest.raises(ApiTimeoutError):
                client.get_json("https://example.org")

            assert mock.call_count == 1


def test_connection_error():
    with ApiClient() as client:
        with patch.object(
            client._session,
            "request",
            side_effect=requests.ConnectionError,
        ):
            with pytest.raises(ApiError):
                client.get_json("https://example.org")


def test_invalid_json():
    with ApiClient() as client:
        with patch.object(
            client._session,
            "request",
            return_value=make_response(body=b"not json"),
        ):
            with pytest.raises(ApiResponseError):
                client.get_json("https://example.org")


def test_empty_response():
    with ApiClient() as client:
        with patch.object(
            client._session,
            "request",
            return_value=make_response(204, b""),
        ):
            with pytest.raises(ApiResponseError):
                client.get_json("https://example.org")


def test_redirect_not_accepted_as_json_success():
    with ApiClient() as client:
        with patch.object(
            client._session,
            "request",
            return_value=make_response(302),
        ):
            with pytest.raises(ApiResponseError):
                client.get_json("https://example.org")


def test_closed_client():
    client = ApiClient()
    client.close()

    with pytest.raises(ApiError):
        client.get_json("https://example.org")


@pytest.mark.parametrize(
    "timeout",
    [
        (0, 2),
        (-1, 2),
        (1, float("inf")),
        (True, 2),
    ],
)
def test_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        ApiClient(timeout=timeout)


def test_invalid_url():
    with ApiClient() as client:
        with pytest.raises(ValueError):
            client.get_json("file:///secret")