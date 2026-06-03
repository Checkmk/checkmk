#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal
from unittest import mock
from unittest.mock import MagicMock

import pytest

import cmk.product_usage.cli as product_usage_cli
from cmk.product_usage.config import load_product_usage_config, ProductUsageAnalyticsSettings
from cmk.product_usage.exceptions import ConfigError
from cmk.utils import http_proxy_config, paths


def test_resolve_proxy_config_falls_back_to_environment_when_no_proxies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The base config carries no configured proxies, so an unknown "global" proxy name must
    # fall back to the environment proxy instead of raising.
    mock_base_config = MagicMock()
    mock_base_config.loaded_config.http_proxies = {}
    monkeypatch.setattr("cmk.base.config.load", MagicMock(return_value=mock_base_config))
    monkeypatch.setattr("cmk.base.app.make_app", MagicMock())

    proxy_config = product_usage_cli.resolve_proxy_config(("global", "missing"))

    assert isinstance(proxy_config, http_proxy_config.EnvironmentProxyConfig)


def test_load_product_usage_config_defaults_when_file_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing/unreadable config file yields the safe 'not_decided' default."""
    monkeypatch.setattr(
        "cmk.product_usage.config.read_config_file", MagicMock(side_effect=ConfigError)
    )

    settings = load_product_usage_config(paths.default_config_dir, mock.Mock())

    assert settings.enabled == "not_decided"
    assert settings.proxy_setting == ("environment", "environment")


@pytest.mark.parametrize("state", ["disabled", "not_decided"])
def test_cron_skips_heavy_work_when_not_enabled(
    monkeypatch: pytest.MonkeyPatch, state: Literal["disabled", "not_decided"]
) -> None:
    """A scheduled run must return early without the heavy proxy load or any collection."""
    monkeypatch.setattr(product_usage_cli, "init_logging", MagicMock())
    monkeypatch.setattr(
        product_usage_cli,
        "load_product_usage_config",
        MagicMock(
            return_value=ProductUsageAnalyticsSettings(
                enabled=state, proxy_setting=("environment", "environment")
            )
        ),
    )
    resolve_spy = MagicMock()
    collect_spy = MagicMock()
    transmit_spy = MagicMock()
    monkeypatch.setattr(product_usage_cli, "resolve_proxy_config", resolve_spy)
    monkeypatch.setattr(product_usage_cli, "collect_data", collect_spy)
    monkeypatch.setattr(product_usage_cli, "transmit_data", transmit_spy)

    assert product_usage_cli.main(["--cron"]) == 0

    resolve_spy.assert_not_called()
    collect_spy.assert_not_called()
    transmit_spy.assert_not_called()


def test_cron_enabled_first_run_only_schedules(monkeypatch: pytest.MonkeyPatch) -> None:
    """The first scheduled run after enabling only plans the next run; it does not collect."""
    monkeypatch.setattr(product_usage_cli, "init_logging", MagicMock())
    monkeypatch.setattr(
        product_usage_cli,
        "load_product_usage_config",
        MagicMock(
            return_value=ProductUsageAnalyticsSettings(
                enabled="enabled", proxy_setting=("environment", "environment")
            )
        ),
    )
    monkeypatch.setattr(product_usage_cli, "get_next_run_ts", MagicMock(return_value=None))
    store_spy = MagicMock()
    resolve_spy = MagicMock()
    collect_spy = MagicMock()
    monkeypatch.setattr(product_usage_cli, "store_next_run_ts", store_spy)
    monkeypatch.setattr(product_usage_cli, "resolve_proxy_config", resolve_spy)
    monkeypatch.setattr(product_usage_cli, "collect_data", collect_spy)

    assert product_usage_cli.main(["--cron"]) == 0

    store_spy.assert_called_once()
    resolve_spy.assert_not_called()
    collect_spy.assert_not_called()


def test_upload_resolves_proxy_and_transmits(monkeypatch: pytest.MonkeyPatch) -> None:
    """The upload path resolves the proxy config and hands it to the transmission."""
    monkeypatch.setattr(product_usage_cli, "init_logging", MagicMock())
    settings = ProductUsageAnalyticsSettings(enabled="enabled", proxy_setting=("no_proxy", None))
    monkeypatch.setattr(
        product_usage_cli, "load_product_usage_config", MagicMock(return_value=settings)
    )
    sentinel_proxy = MagicMock()
    resolve_spy = MagicMock(return_value=sentinel_proxy)
    transmit_spy = MagicMock()
    monkeypatch.setattr(product_usage_cli, "resolve_proxy_config", resolve_spy)
    monkeypatch.setattr(product_usage_cli, "transmit_data", transmit_spy)

    assert product_usage_cli.main(["--upload"]) == 0

    resolve_spy.assert_called_once_with(("no_proxy", None))
    transmit_spy.assert_called_once()
    assert transmit_spy.call_args.kwargs["proxy_config"] is sentinel_proxy


def test_parse_args_cron_enables_all_phases() -> None:
    assert product_usage_cli.parse_args(["--cron"]) == product_usage_cli.ProductUsageRequest(
        collect=True, store=True, upload=True, schedule=True
    )


def test_parse_args_collection_collects_and_stores() -> None:
    assert product_usage_cli.parse_args(["--collection"]) == product_usage_cli.ProductUsageRequest(
        collect=True, store=True
    )


def test_parse_args_dry_run_collects_only() -> None:
    assert product_usage_cli.parse_args(["--dry-run"]) == product_usage_cli.ProductUsageRequest(
        collect=True
    )


def test_parse_args_upload_only() -> None:
    assert product_usage_cli.parse_args(["--upload"]) == product_usage_cli.ProductUsageRequest(
        upload=True
    )
