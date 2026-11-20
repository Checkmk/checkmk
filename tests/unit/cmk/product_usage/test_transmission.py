#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TypedDict
from unittest import mock
from unittest.mock import patch

import pytest
import requests
import urllib3
from pytest_mock import MockerFixture

from cmk.product_usage.exceptions import EndpointUnreachableError, InvalidProductUsageEndpointError
from cmk.product_usage.transmission import _get_api_url, DEFAULT_PROXY, transmit_data
from cmk.utils import http_proxy_config


class FileInfo(TypedDict):
    filename: str
    success: bool


@pytest.mark.parametrize(
    ("files", "grafana_info_deleted"),
    [
        ([], False),
        ([{"filename": "product_usage_1.json", "success": True}], True),
        ([{"filename": "product_usage_1.json", "success": False}], False),
        (
            [
                {"filename": "product_usage_1.json", "success": True},
                {"filename": "product_usage_2.json", "success": False},
            ],
            False,
        ),
        (
            [
                {"filename": "product_usage_1.json", "success": False},
                {"filename": "product_usage_2.json", "success": False},
                {"filename": "product_usage_10.json", "success": False},
                {"filename": "product_usage_99.json", "success": True},
            ],
            True,
        ),
    ],
)
def test_transmission(
    files: list[FileInfo], grafana_info_deleted: bool, tmp_path: Path, mocker: MockerFixture
) -> None:
    mocked_product_usage_dir = tmp_path / "product_usage"
    mocked_product_usage_dir.mkdir(parents=True, exist_ok=True)

    mocks = []

    (mocked_product_usage_dir / "grafana_usage.json").write_text("{}")
    # Create test files and mock responses
    for file in files:
        (mocked_product_usage_dir / file["filename"]).write_text("{}")
        mocked = mocker.Mock()
        mocked.return_value.ok = file["success"]
        mocks.append(mocked.return_value)

    with patch("requests.post") as mock_post:
        mock_post.side_effect = mocks
        transmit_data(tmp_path, logger=mock.Mock())

    for file in files:
        file_path = mocked_product_usage_dir / file["filename"]
        if file["success"]:
            assert not file_path.exists()
        else:
            assert file_path.exists()

    assert (mocked_product_usage_dir / "grafana_usage.json").exists() != grafana_info_deleted


@pytest.mark.parametrize(
    ("proxy_config", "expected_requests_proxies"),
    [
        (DEFAULT_PROXY, None),
        (http_proxy_config.NoProxyConfig(), {"http": "", "https": ""}),
        (http_proxy_config.EnvironmentProxyConfig(), None),
        (http_proxy_config.ExplicitProxyConfig("hello"), {"http": "hello", "https": "hello"}),
    ],
)
def test_transmission_with_proxy(
    proxy_config: http_proxy_config.HTTPProxyConfig,
    expected_requests_proxies: dict[str, str] | None,
    tmp_path: Path,
) -> None:
    mocked_product_usage_dir = tmp_path / "product_usage"
    mocked_product_usage_dir.mkdir(parents=True, exist_ok=True)
    (mocked_product_usage_dir / "product_usage_1.json").write_text("{}")

    mock_response = mock.Mock()
    mock_response.ok = True

    with patch("requests.post", return_value=mock_response) as mock_post:
        transmit_data(tmp_path, proxy_config=proxy_config, logger=mock.Mock())

    assert mock_post.call_count == 1
    assert mock_post.call_args.kwargs["proxies"] == expected_requests_proxies


@pytest.mark.parametrize(
    "url, valid",
    [
        ("", False),
        ("https://checkmk.com", True),
        ("https://checkmk.com/path", True),
        ("https://analytics.checkmk.com/upload", True),
        ("ftp://checkmk.com", False),
        ("http://checkmk.com", False),
        ("https://", False),
        ("https://?.com", False),
        ("https://#.com", False),
    ],
)
def test_get_api_url(url: str, valid: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CMK_PRODUCT_USAGE_URL", url)

    if valid:
        assert url == _get_api_url()
    else:
        with pytest.raises(InvalidProductUsageEndpointError):
            _get_api_url()


def _write_payload_file(var_dir: Path) -> Path:
    directory = var_dir / "product_usage"
    directory.mkdir(parents=True, exist_ok=True)
    payload_file = directory / "product_usage_1.json"
    payload_file.write_text("{}")
    return payload_file


def _transmit_failing(
    var_dir: Path,
    *,
    resolve: Callable[[str], Sequence[str]],
    proxy_config: http_proxy_config.HTTPProxyConfig | None = None,
) -> str:
    _write_payload_file(var_dir)
    with (
        patch(
            "requests.post", side_effect=requests.exceptions.SSLError("certificate verify failed")
        ),
        pytest.raises(EndpointUnreachableError) as excinfo,
    ):
        transmit_data(
            var_dir,
            logger=mock.Mock(),
            proxy_config=proxy_config or http_proxy_config.NoProxyConfig(),
            resolve=resolve,
        )
    return str(excinfo.value)


@pytest.mark.parametrize("address", ["127.0.0.1", "0.0.0.0", "::1"])
def test_unreachable_endpoint_on_blocked_address_points_to_dns_block_list(
    tmp_path: Path, address: str
) -> None:
    message = _transmit_failing(tmp_path, resolve=lambda _host: [address])

    assert f"resolves to {address}" in message
    assert "DNS block list" in message


def test_unreachable_endpoint_on_public_address_names_no_cause(tmp_path: Path) -> None:
    message = _transmit_failing(tmp_path, resolve=lambda _host: ["203.0.113.5"])

    assert message == (
        "Could not connect to analytics.checkmk.com (certificate verify failed)."
        " The data is sent with the next run."
    )


def test_unreachable_endpoint_without_dns_answer_says_so(tmp_path: Path) -> None:
    def resolve(_host: str) -> Sequence[str]:
        raise socket.gaierror("Name or service not known")

    message = _transmit_failing(tmp_path, resolve=resolve)

    assert "the host name can not be resolved" in message


def test_unreachable_endpoint_via_proxy_skips_the_dns_heuristic(tmp_path: Path) -> None:
    def resolve(_host: str) -> Sequence[str]:
        raise AssertionError("The proxy resolves the host name, not the site")

    message = _transmit_failing(
        tmp_path,
        resolve=resolve,
        proxy_config=http_proxy_config.ExplicitProxyConfig("http://proxy.example.com:3128"),
    )

    assert "via the configured proxy" in message


def test_unreachable_endpoint_keeps_the_data_for_the_next_run(tmp_path: Path) -> None:
    _transmit_failing(tmp_path, resolve=lambda _host: ["127.0.0.1"])

    assert (tmp_path / "product_usage" / "product_usage_1.json").exists()


def test_unreachable_endpoint_names_the_innermost_cause(tmp_path: Path) -> None:
    _write_payload_file(tmp_path)
    # Built like urllib3 and requests chain the errors of a refused connection
    new_connection_error = urllib3.exceptions.NewConnectionError(
        None,  # type: ignore[arg-type]
        "Failed to establish a new connection: [Errno 111] Connection refused",
    )
    new_connection_error.__cause__ = ConnectionRefusedError(111, "Connection refused")
    error = requests.exceptions.ConnectionError(
        urllib3.exceptions.MaxRetryError(
            pool=None,  # type: ignore[arg-type]
            url="/upload",
            reason=new_connection_error,
        )
    )

    with (
        patch("requests.post", side_effect=error),
        pytest.raises(EndpointUnreachableError) as excinfo,
    ):
        transmit_data(
            tmp_path,
            logger=mock.Mock(),
            proxy_config=http_proxy_config.NoProxyConfig(),
            resolve=lambda _host: ["203.0.113.5"],
        )

    assert str(excinfo.value) == (
        "Could not connect to analytics.checkmk.com ([Errno 111] Connection refused)."
        " The data is sent with the next run."
    )
