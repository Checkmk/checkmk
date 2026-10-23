#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.rulesets.internal.form_specs import (
    migrate_to_internal_proxy,
    parse_proxy_url,
    ParsedProxyUrl,
)


@pytest.mark.parametrize(
    "url, expected",
    [
        pytest.param(
            "http://proxy.lan:3128",
            ParsedProxyUrl(
                proxy={"scheme": "http", "proxy_server_name": "proxy.lan", "port": 3128},
                credentials=None,
            ),
            id="plain",
        ),
        pytest.param(
            "socks5h://us%3Aer:p%40ss@proxy.lan:1080/",
            ParsedProxyUrl(
                proxy={"scheme": "socks5h", "proxy_server_name": "proxy.lan", "port": 1080},
                credentials=("us:er", "p@ss"),
            ),
            id="credentials are decoded",
        ),
        pytest.param(
            "https://user@proxy.lan",
            ParsedProxyUrl(
                proxy={"scheme": "https", "proxy_server_name": "proxy.lan", "port": 443},
                credentials=("user", ""),
            ),
            id="user without password, default port",
        ),
        pytest.param(
            "Proxy.LAN:3128",
            ParsedProxyUrl(
                proxy={"scheme": "http", "proxy_server_name": "proxy.lan", "port": 3128},
                credentials=None,
            ),
            id="no scheme, host is lower-cased",
        ),
        pytest.param(
            "http://[fe80::1]:3128",
            ParsedProxyUrl(
                proxy={"scheme": "http", "proxy_server_name": "[fe80::1]", "port": 3128},
                credentials=None,
            ),
            id="IPv6",
        ),
        pytest.param(
            "http://proxy.lan:3128/some/path?query#fragment",
            ParsedProxyUrl(
                proxy={"scheme": "http", "proxy_server_name": "proxy.lan", "port": 3128},
                credentials=None,
            ),
            id="path is dropped",
        ),
        pytest.param(
            "http://proxy.lan:",
            ParsedProxyUrl(
                proxy={"scheme": "http", "proxy_server_name": "proxy.lan", "port": 80},
                credentials=None,
            ),
            id="empty port",
        ),
    ],
)
def test_parse_proxy_url(url: str, expected: ParsedProxyUrl) -> None:
    assert parse_proxy_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("ftp://proxy.lan:21", id="unsupported scheme"),
        pytest.param("http://proxy.lan:port", id="invalid port"),
        pytest.param("http://user:pw@:3128", id="no host"),
        pytest.param("http://:pw@proxy.lan:3128", id="password without user"),
        pytest.param("http://proxy.lan:0", id="port 0"),
    ],
)
def test_parse_proxy_url_rejects_urls_without_structured_form(url: str) -> None:
    assert parse_proxy_url(url) is None


@pytest.mark.parametrize(
    "legacy_value",
    [
        pytest.param(("url", "http://proxy.lan:3128"), id="valuespec"),
        pytest.param(("cmk_postprocessed", "explicit_proxy", "http://proxy.lan:3128"), id="Proxy"),
    ],
)
def test_migrate_explicit_proxy_url(legacy_value: object) -> None:
    assert migrate_to_internal_proxy(legacy_value) == (
        "cmk_postprocessed",
        "explicit_proxy",
        {"scheme": "http", "proxy_server_name": "proxy.lan", "port": 3128},
    )


def test_migrate_explicit_proxy_url_moves_credentials_into_explicit_password() -> None:
    match migrate_to_internal_proxy(
        ("cmk_postprocessed", "explicit_proxy", "http://user:s3crit@proxy.lan:3128")
    ):
        case (
            "cmk_postprocessed",
            "explicit_proxy",
            {
                "auth": {
                    "user": "user",
                    "password": ("cmk_postprocessed", "explicit_password", (_, "s3crit")),
                }
            },
        ):
            pass
        case other:
            pytest.fail(f"Unexpected migration result: {other!r}")


def test_migrate_structured_proxy_is_idempotent() -> None:
    value = (
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
    )
    assert migrate_to_internal_proxy(value) == value


@pytest.mark.parametrize(
    "url, user",
    [
        pytest.param("http://user:s3crit@proxy.lan:port", "user", id="invalid port"),
        pytest.param("http://:s3crit@proxy.lan:3128", "", id="password without user"),
        pytest.param("user:s3crit@proxy.lan:port", "user", id="no scheme"),
    ],
)
def test_migrate_unconvertible_proxy_url_keeps_the_credentials(url: str, user: str) -> None:
    match migrate_to_internal_proxy(("cmk_postprocessed", "explicit_proxy", url)):
        case (
            "cmk_postprocessed",
            "explicit_proxy",
            {
                "proxy_server_name": "proxy.lan",
                "port": 0,
                "auth": {
                    "user": str() as migrated_user,
                    "password": ("cmk_postprocessed", "explicit_password", (_, "s3crit")),
                },
            },
        ) if migrated_user == user:
            pass
        case other:
            pytest.fail(f"Unexpected migration result: {other!r}")
