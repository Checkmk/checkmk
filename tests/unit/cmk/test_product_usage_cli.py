#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest import mock
from unittest.mock import MagicMock

import pytest

import cmk.product_usage.config
import cmk.product_usage_cli
from cmk.product_usage.config import ProductUsageAnalyticsSettings
from cmk.product_usage.exceptions import ConfigError
from cmk.utils import http_proxy_config


def test_load_product_usage_config_with_missing_http_proxies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Mock the load function to return a config with empty http_proxies
    mock_config = MagicMock()
    mock_config.loaded_config.http_proxies = {}

    mock_load = MagicMock(return_value=mock_config)
    monkeypatch.setattr("cmk.product_usage_cli.load", mock_load)
    monkeypatch.setattr("cmk.product_usage_cli.make_app", MagicMock())

    # Mock the config read from file variable directly
    config_from_file = ProductUsageAnalyticsSettings(
        enabled="enabled",
        proxy_setting=("global", ""),
    )

    # Mock read_config_file to return config_from_file
    mock_read_config = MagicMock(return_value=config_from_file)
    monkeypatch.setattr("cmk.product_usage.config.read_config_file", mock_read_config)

    # Should not raise KeyError
    config = cmk.product_usage_cli.load_config(logger=mock.Mock())

    # Should respect the provided value and use default for missing
    assert config.enabled is True
    assert config.state == "enabled"
    # Should fall back to environment proxy since http_proxies is empty
    assert isinstance(config.proxy_config, http_proxy_config.EnvironmentProxyConfig)


def test_load_config_with_missing_config_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that load_config return default values when read_config_file raises."""
    # Mock the load function to return a config with empty http_proxies
    mock_config = MagicMock()
    mock_config.loaded_config.http_proxies = {}

    mock_load = MagicMock(return_value=mock_config)
    monkeypatch.setattr("cmk.product_usage_cli.load", mock_load)
    monkeypatch.setattr("cmk.product_usage_cli.make_app", MagicMock())

    with mock.patch("cmk.product_usage.config.read_config_file", side_effect=ConfigError):
        config = cmk.product_usage_cli.load_config(logger=mock.Mock())

        # Should have default values
        assert config.enabled is False
        assert config.state == "not_decided"
        assert isinstance(config.proxy_config, http_proxy_config.EnvironmentProxyConfig)
