#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest import mock

import pytest
from werkzeug.datastructures import Headers

import cmk.product_usage.collectors.grafana as grafana_collector
from cmk.utils.paths import var_dir


@pytest.fixture(autouse=True)
def init_grafana_usage_directory() -> None:
    grafana_collector._grafana_usage_file_path(var_dir).parent.mkdir(parents=True, exist_ok=True)


def test_collect_when_grafana_not_used() -> None:
    data = grafana_collector.collect(var_dir)

    assert data is None


@pytest.mark.parametrize(
    ("headers", "expected_version", "expected_is_used", "expected_is_grafana_cloud"),
    [
        (
            {
                "X-Grafana-Org-Id": "1",
                "User-Agent": "Grafana/1",
                "X-Grafana-Referer": "https://self-hosted.com",
            },
            "1",
            True,
            False,
        ),
        (
            {
                "X-Grafana-Org-Id": "1",
                "User-Agent": "Grafana/0.1.0p123",
                "X-Grafana-Referer": "https://checkmk.grafana.net",
            },
            "0.1.0p123",
            True,
            True,
        ),
        (
            {
                "X-Grafana-Org-Id": "1",
                "User-Agent": "Grafana/2",
                "X-Grafana-Referer": "https://notcloud.grafana.net.self-hosted.com",
            },
            "2",
            True,
            False,
        ),
    ],
)
def test_grafana_data_collector(
    headers: dict[str, str],
    expected_version: str,
    expected_is_used: bool,
    expected_is_grafana_cloud: bool,
) -> None:
    grafana_collector.store_usage_data(
        headers=Headers(headers), var_dir=var_dir, logger=mock.Mock()
    )

    data = grafana_collector.collect(var_dir)

    assert data is not None
    assert data.version == expected_version
    assert data.is_used is expected_is_used
    assert data.is_grafana_cloud is expected_is_grafana_cloud


def test_grafana_data_collector_not_used() -> None:
    headers: dict[str, str] = {
        "NotAGrafanaHeader": "1",
    }
    grafana_collector.store_usage_data(
        headers=Headers(headers), var_dir=var_dir, logger=mock.Mock()
    )

    data = grafana_collector.collect(var_dir)

    assert data is None


def test_grafana_data_collector_unexpected_error() -> None:
    headers_mock = mock.Mock()
    headers_mock.get.side_effect = RuntimeError("unexpected")

    logger_mock = mock.Mock()

    grafana_collector.store_usage_data(headers=headers_mock, var_dir=var_dir, logger=logger_mock)

    logger_mock.error.assert_called_once_with("Store Grafana usage failed", exc_info=True)


def test_grafana_data_collector_store_usage_data_twice() -> None:
    headers = {
        "X-Grafana-Org-Id": "1",
        "User-Agent": "Grafana/1",
        "X-Grafana-Referer": "https://whatever.com",
    }
    grafana_collector.store_usage_data(
        headers=Headers(headers), var_dir=var_dir, logger=mock.Mock()
    )
    # Storing the usage data twice should not raise an error
    grafana_collector.store_usage_data(
        headers=Headers(headers), var_dir=var_dir, logger=mock.Mock()
    )


def test_remove_grafana_usage_data() -> None:
    headers = {
        "X-Grafana-Org-Id": "1",
        "User-Agent": "Grafana/1",
        "X-Grafana-Referer": "https://whatever.com",
    }
    grafana_collector.store_usage_data(
        headers=Headers(headers), var_dir=var_dir, logger=mock.Mock()
    )

    data = grafana_collector.collect(var_dir)
    assert data is not None

    grafana_collector.remove_grafana_usage_data(var_dir)

    data = grafana_collector.collect(var_dir)
    assert data is None
