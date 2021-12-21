#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Tuple, Union

import pytest

from cmk.utils.http_proxy_config import (
    EnvironmentProxyConfig,
    ExplicitProxyConfig,
    http_proxy_config_from_user_setting,
    HTTPProxyConfig,
    NoProxyConfig,
)

_PROXIES_GLOBAL_SETTINGS = {
    "http_blub": {
        "ident": "blub",
        "title": "HTTP blub",
        "proxy_url": "http://blub:8080",
    },
    "https_blub": {
        "ident": "blub",
        "title": "HTTPS blub",
        "proxy_url": "https://blub:8181",
    },
    "socks5_authed": {
        "ident": "socks5",
        "title": "HTTP socks5 authed",
        "proxy_url": "socks5://us%3Aer:s%40crit@socks.proxy:443",
    },
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
    ],
)
def test_http_proxy_config_from_user_setting(
    rulesepc_value: Union[str, Tuple[str, Optional[str]]],
    expected_result: HTTPProxyConfig,
) -> None:
    assert (
        http_proxy_config_from_user_setting(
            rulesepc_value,  # type: ignore[arg-type]  # we also test the legacy case
            _PROXIES_GLOBAL_SETTINGS,
        )
        == expected_result
    )
