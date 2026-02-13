#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pprint
import typing
from pathlib import Path

import pytest

from cmk.product_usage.config import (
    get_proxy_config,
    ProxySetting,
    read_config_file,
)
from cmk.product_usage.exceptions import ConfigError
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


def test_read_config_file_with_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        read_config_file(Path("/non_existent_directory"))


def test_read_config_file_with_corrupt_data_in_file_returns_defaults(tmp_path: Path) -> None:
    mocked_config_dir = tmp_path / "etc/check_mk"
    mocked_config_dir.mkdir(parents=True, exist_ok=True)

    (mocked_config_dir / "product_usage_analytics.mk").write_text("")

    config = read_config_file(mocked_config_dir)
    assert config.enabled == "not_decided"
    assert config.proxy_setting == ("environment", "environment")

    (mocked_config_dir / "product_usage_analytics.mk").write_text("{}")

    config = read_config_file(mocked_config_dir)

    assert config.enabled == "not_decided"
    assert config.proxy_setting == ("environment", "environment")

    output = f"product_usage_analytics = {pprint.pformat({'enabled': 'enabled'})}"

    (mocked_config_dir / "product_usage_analytics.mk").write_text(output)

    config = read_config_file(mocked_config_dir)

    assert config.enabled == "enabled"
    assert config.proxy_setting == ("environment", "environment")


def test_read_config_file_with_valid_data(tmp_path: Path) -> None:
    mocked_config_dir = tmp_path / "etc/check_mk"
    mocked_config_dir.mkdir(parents=True, exist_ok=True)

    output = f"product_usage_analytics = {pprint.pformat({'enabled': 'enabled', 'proxy_setting': ('no_proxy', None)})}"

    (mocked_config_dir / "product_usage_analytics.mk").write_text(output)

    config = read_config_file(mocked_config_dir)
    assert config.enabled == "enabled"
    assert config.proxy_setting == ("no_proxy", None)
