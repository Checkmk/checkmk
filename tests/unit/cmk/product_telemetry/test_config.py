#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing
from unittest.mock import MagicMock

import pytest

from cmk.base.default_config.telemetry import ProxySetting
from cmk.product_telemetry.config import get_proxy_config, load_telemetry_config
from cmk.utils import http_proxy_config


@pytest.fixture
def global_settings_proxies() -> typing.Mapping[str, http_proxy_config.HTTPProxySpec]:
    return {
        "proxy123": http_proxy_config.HTTPProxySpec(
            ident="proxy123",
            title="Proxy 123",
            proxy_config=http_proxy_config.ProxyConfigSpec(
                scheme="https",
                proxy_server_name="global_proxy.company.com",
                port=456,
            ),
        )
    }


@pytest.mark.parametrize(
    ("proxy_setting", "expected_proxy_config"),
    [
        pytest.param(
            ("no_proxy", None),
            http_proxy_config.NoProxyConfig(),
            id="no proxy",
        ),
        pytest.param(
            ("environment", "environment"),
            http_proxy_config.EnvironmentProxyConfig(),
            id="environment proxy",
        ),
        pytest.param(
            (
                "url",
                http_proxy_config.ProxyConfigSpec(
                    scheme="http", proxy_server_name="company.com", port=123
                ),
            ),
            http_proxy_config.ExplicitProxyConfig("http://company.com:123"),
            id="proxy without auth",
        ),
        pytest.param(
            (
                "url",
                http_proxy_config.ProxyConfigSpec(
                    scheme="http",
                    proxy_server_name="company.com",
                    port=123,
                    auth=http_proxy_config.ProxyAuthSpec(
                        user="foo",
                        password=(
                            "cmk_postprocessed",
                            "explicit_password",
                            ("pass_id", "password"),
                        ),
                    ),
                ),
            ),
            http_proxy_config.ExplicitProxyConfig("http://foo:password@company.com:123"),
            id="proxy with auth (explicit password)",
        ),
        pytest.param(
            ("global", "proxy123"),
            http_proxy_config.ExplicitProxyConfig("https://global_proxy.company.com:456"),
            id="global proxy without auth",
        ),
        pytest.param(
            ("global", "unknown"),
            http_proxy_config.EnvironmentProxyConfig(),
            id="unknown global proxy",
        ),
    ],
)
def test_get_proxy_config(
    proxy_setting: ProxySetting,
    expected_proxy_config: http_proxy_config.HTTPProxyConfig,
    global_settings_proxies: typing.Mapping[str, http_proxy_config.HTTPProxySpec],
) -> None:
    proxy_config = get_proxy_config(proxy_setting, global_proxies=global_settings_proxies)

    assert proxy_config == expected_proxy_config


def test_load_telemetry_config_with_missing_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that load_telemetry_config handles missing keys gracefully."""
    # Mock the load function to return a config with incomplete product_telemetry
    mock_config = MagicMock()
    mock_config.loaded_config.product_telemetry = {}  # Missing both keys
    mock_config.loaded_config.http_proxies = {}

    mock_load = MagicMock(return_value=mock_config)
    monkeypatch.setattr("cmk.product_telemetry.config.load", mock_load)
    monkeypatch.setattr("cmk.product_telemetry.config.make_app", MagicMock())

    # Should not raise KeyError
    config = load_telemetry_config()

    # Should have default values
    assert config.enabled is False
    assert config.state == "not_decided"
    assert isinstance(config.proxy_config, http_proxy_config.EnvironmentProxyConfig)


def test_load_telemetry_config_with_partial_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that load_telemetry_config handles partial configuration."""
    # Mock the load function to return a config with only enable_telemetry
    mock_config = MagicMock()
    mock_config.loaded_config.product_telemetry = {"enable_telemetry": "enabled"}
    mock_config.loaded_config.http_proxies = {}

    mock_load = MagicMock(return_value=mock_config)
    monkeypatch.setattr("cmk.product_telemetry.config.load", mock_load)
    monkeypatch.setattr("cmk.product_telemetry.config.make_app", MagicMock())

    # Should not raise KeyError
    config = load_telemetry_config()

    # Should respect the provided value and use default for missing
    assert config.enabled is True
    assert config.state == "enabled"
    assert isinstance(config.proxy_config, http_proxy_config.EnvironmentProxyConfig)
