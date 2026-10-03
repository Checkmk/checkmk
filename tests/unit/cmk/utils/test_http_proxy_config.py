#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Literal

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.utils import password_store
from cmk.utils.http_proxy_config import (
    EnvironmentProxyConfig,
    ExplicitProxyConfig,
    http_proxy_config_from_user_setting,
    HTTPProxyConfig,
    HTTPProxySpec,
    NoProxyConfig,
    ProxyAuthSpec,
    ProxyConfigSpec,
)

_PROXIES_GLOBAL_SETTINGS: Mapping[str, HTTPProxySpec] = {
    "http_blub": HTTPProxySpec(
        ident="blub",
        title="HTTP blub",
        proxy_config=ProxyConfigSpec(
            scheme="http",
            proxy_server_name="blub",
            port=8080,
        ),
    ),
    "https_blab": HTTPProxySpec(
        ident="blab",
        title="HTTPS blab",
        proxy_config=ProxyConfigSpec(
            scheme="https",
            proxy_server_name="blab",
            port=8181,
        ),
    ),
    "https_blub": HTTPProxySpec(
        ident="blub",
        title="HTTPS blub",
        proxy_config=ProxyConfigSpec(
            scheme="https",
            proxy_server_name="blub",
            port=8181,
        ),
    ),
    "socks5_authed": HTTPProxySpec(
        ident="socks5",
        title="HTTP socks5 authed",
        proxy_config=ProxyConfigSpec(
            scheme="socks5",
            proxy_server_name="socks.proxy",
            port=443,
            auth=ProxyAuthSpec(
                user="us:er",
                password=(
                    "cmk_postprocessed",
                    "explicit_password",
                    ("password", "s@crit"),
                ),
            ),
        ),
    ),
}


@pytest.mark.parametrize(
    "rulesepc_value, expected_result",
    [
        pytest.param(
            "bla",
            EnvironmentProxyConfig(),
            id="legacy case",
        ),
        pytest.param(
            (
                "no_proxy",
                None,
            ),
            NoProxyConfig(),
            id="no proxy",
        ),
        pytest.param(
            (
                "environment",
                None,
            ),
            EnvironmentProxyConfig(),
            id="from environment",
        ),
        pytest.param(
            (
                "global",
                "not_existing",
            ),
            EnvironmentProxyConfig(),
            id="global proxy, missing",
        ),
        pytest.param(
            (
                "global",
                "http_blub",
            ),
            ExplicitProxyConfig("http://blub:8080"),
            id="global proxy http",
        ),
        pytest.param(
            (
                "global",
                "https_blub",
            ),
            ExplicitProxyConfig("https://blub:8181"),
            id="global proxy https",
        ),
        pytest.param(
            (
                "global",
                "socks5_authed",
            ),
            ExplicitProxyConfig("socks5://us%3Aer:s%40crit@socks.proxy:443"),
            id="global proxy socks5",
        ),
        pytest.param(
            (
                "url",
                "http://8.4.2.1:1337",
            ),
            ExplicitProxyConfig("http://8.4.2.1:1337"),
            id="explicitly configured",
        ),
        pytest.param(
            ("cmk_postprocessed", "environment", ""),
            EnvironmentProxyConfig(),
            id="FormSpec from environment",
        ),
        pytest.param(
            ("cmk_postprocessed", "explicit_proxy", "http://11.11.19.81:2020"),
            ExplicitProxyConfig("http://11.11.19.81:2020"),
            id="FormSpec explicitly configured",
        ),
        pytest.param(
            ("cmk_postprocessed", "stored_proxy", "https_blab"),
            ExplicitProxyConfig("https://blab:8181"),
            id="FormSpec global proxy https",
        ),
        pytest.param(
            ("cmk_postprocessed", "no_proxy", ""),
            NoProxyConfig(),
            id="FormSpec no proxy",
        ),
        pytest.param(
            ["cmk_postprocessed", "environment_proxy", ""],
            EnvironmentProxyConfig(),
            id="FormSpec from environment as list",
        ),
        pytest.param(
            ["cmk_postprocessed", "explicit_proxy", "http://11.11.19.81:2020"],
            ExplicitProxyConfig("http://11.11.19.81:2020"),
            id="FormSpec explicitly configured as list",
        ),
        pytest.param(
            ["cmk_postprocessed", "stored_proxy", "https_blab"],
            ExplicitProxyConfig("https://blab:8181"),
            id="FormSpec global proxy https as list",
        ),
        pytest.param(
            ["cmk_postprocessed", "no_proxy", ""],
            NoProxyConfig(),
            id="FormSpec no proxy as list",
        ),
        pytest.param(
            ["only_one_element"],
            EnvironmentProxyConfig(),
            id="malformed list falls back instead of crashing",
        ),
        pytest.param(
            ["a", "b", "c", "d"],
            EnvironmentProxyConfig(),
            id="oversized list falls back instead of crashing",
        ),
    ],
)
def test_http_proxy_config_from_user_setting(
    rulesepc_value: str
    | list[str]
    | tuple[str, str | None]
    | tuple[
        Literal["cmk_postprocessed"],
        Literal["environment_proxy", "no_proxy", "stored_proxy", "explicit_proxy"],
        str,
    ],
    expected_result: HTTPProxyConfig,
) -> None:
    assert (
        http_proxy_config_from_user_setting(
            rulesepc_value,  # type: ignore[arg-type]  # we also test the legacy case
            _PROXIES_GLOBAL_SETTINGS,
        )
        == expected_result
    )


@pytest.mark.parametrize(
    "rulespec_value, expected_result",
    [
        pytest.param(
            (
                "cmk_postprocessed",
                "explicit_proxy",
                {"scheme": "http", "proxy_server_name": "proxy.lan", "port": 3128},
            ),
            ExplicitProxyConfig("http://proxy.lan:3128"),
            id="without authentication",
        ),
        pytest.param(
            (
                "cmk_postprocessed",
                "explicit_proxy",
                {
                    "scheme": "socks5h",
                    "proxy_server_name": "proxy.lan",
                    "port": 1080,
                    "auth": {
                        "user": "user",
                        "password": ("cmk_postprocessed", "explicit_password", ("uuid1", "s3crit")),
                    },
                },
            ),
            ExplicitProxyConfig("socks5h://user:s3crit@proxy.lan:1080"),
            id="explicit password",
        ),
    ],
)
def test_structured_explicit_proxy_resolves_to_its_url(
    rulespec_value: object, expected_result: HTTPProxyConfig
) -> None:
    assert (
        http_proxy_config_from_user_setting(
            rulespec_value,  # type: ignore[arg-type]
            {},
        )
        == expected_result
    )


def test_structured_explicit_proxy_with_stored_password() -> None:
    password_store.save({"proxy_pw": "s3crit"}, password_store.pending_secrets_path_site())

    assert http_proxy_config_from_user_setting(
        (
            "cmk_postprocessed",
            "explicit_proxy",
            {
                "scheme": "http",
                "proxy_server_name": "proxy.lan",
                "port": 3128,
                "auth": {
                    "user": "user",
                    "password": ("cmk_postprocessed", "stored_password", ("proxy_pw", "")),
                },
            },
        ),
        {},
    ) == ExplicitProxyConfig("http://user:s3crit@proxy.lan:3128")


def test_structured_explicit_proxy_with_missing_stored_password_raises() -> None:
    with pytest.raises(MKGeneralException):
        http_proxy_config_from_user_setting(
            (
                "cmk_postprocessed",
                "explicit_proxy",
                {
                    "scheme": "http",
                    "proxy_server_name": "proxy.lan",
                    "port": 3128,
                    "auth": {
                        "user": "user",
                        "password": ("cmk_postprocessed", "stored_password", ("missing", "")),
                    },
                },
            ),
            {},
        )


@pytest.mark.parametrize(
    "proxy_config",
    [
        pytest.param({"scheme": "http", "proxy_server_name": "proxy.lan"}, id="missing port"),
        pytest.param(
            {
                "scheme": "http",
                "proxy_server_name": "proxy.lan",
                "port": 3128,
                "auth": {"user": "user"},
            },
            id="missing password",
        ),
    ],
)
def test_malformed_structured_explicit_proxy_raises(proxy_config: Mapping[str, object]) -> None:
    with pytest.raises(ValueError):
        http_proxy_config_from_user_setting(
            ("cmk_postprocessed", "explicit_proxy", proxy_config),
            {},
        )


def test_credentials_are_encoded_in_the_proxy_url() -> None:
    assert http_proxy_config_from_user_setting(
        (
            "cmk_postprocessed",
            "explicit_proxy",
            {
                "scheme": "http",
                "proxy_server_name": "proxy.lan",
                "port": 3128,
                "auth": {
                    "user": "dom\\us:er",
                    "password": (
                        "cmk_postprocessed",
                        "explicit_password",
                        ("uuid1", "p@ss/w:rd%41"),
                    ),
                },
            },
        ),
        {},
    ) == ExplicitProxyConfig("http://dom%5Cus%3Aer:p%40ss%2Fw%3Ard%2541@proxy.lan:3128")
