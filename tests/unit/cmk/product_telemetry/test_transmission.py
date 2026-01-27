#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import TypedDict
from unittest import mock
from unittest.mock import patch

import pytest
from pytest_mock import MockerFixture

from cmk.product_telemetry.exceptions import InvalidTelemetryEndpointError
from cmk.product_telemetry.transmission import _get_api_url, DEFAULT_PROXY, transmit_telemetry_data
from cmk.utils import http_proxy_config


class FileInfo(TypedDict):
    filename: str
    success: bool


@pytest.mark.parametrize(
    ("files", "grafana_info_deleted"),
    [
        ([], False),
        ([{"filename": "telemetry_1.json", "success": True}], True),
        ([{"filename": "telemetry_1.json", "success": False}], False),
        (
            [
                {"filename": "telemetry_1.json", "success": True},
                {"filename": "telemetry_2.json", "success": False},
            ],
            False,
        ),
        (
            [
                {"filename": "telemetry_1.json", "success": False},
                {"filename": "telemetry_2.json", "success": False},
                {"filename": "telemetry_10.json", "success": False},
                {"filename": "telemetry_99.json", "success": True},
            ],
            True,
        ),
    ],
)
def test_transmission(
    files: list[FileInfo], grafana_info_deleted: bool, tmp_path: Path, mocker: MockerFixture
) -> None:
    mocked_telemetry_dir = tmp_path / "telemetry"
    mocked_telemetry_dir.mkdir(parents=True, exist_ok=True)

    mocks = []

    (mocked_telemetry_dir / "grafana_usage.json").write_text("{}")
    # Create test files and mock responses
    for file in files:
        (mocked_telemetry_dir / file["filename"]).write_text("{}")
        mocked = mocker.Mock()
        mocked.return_value.ok = file["success"]
        mocks.append(mocked.return_value)

    with patch("requests.post") as mock_post:
        mock_post.side_effect = mocks
        transmit_telemetry_data(tmp_path, logger=mock.Mock())

    for file in files:
        file_path = mocked_telemetry_dir / file["filename"]
        if file["success"]:
            assert not file_path.exists()
        else:
            assert file_path.exists()

    assert (mocked_telemetry_dir / "grafana_usage.json").exists() != grafana_info_deleted


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
    mocked_telemetry_dir = tmp_path / "telemetry"
    mocked_telemetry_dir.mkdir(parents=True, exist_ok=True)
    (mocked_telemetry_dir / "telemetry_1.json").write_text("{}")

    mock_response = mock.Mock()
    mock_response.ok = True

    with patch("requests.post", return_value=mock_response) as mock_post:
        transmit_telemetry_data(tmp_path, proxy_config=proxy_config, logger=mock.Mock())

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
    monkeypatch.setenv("CMK_TELEMETRY_URL", url)

    if valid:
        assert url == _get_api_url()
    else:
        with pytest.raises(InvalidTelemetryEndpointError):
            _get_api_url()
