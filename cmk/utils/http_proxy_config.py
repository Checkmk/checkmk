#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from typing import Literal, Protocol


class HTTPProxyConfig(Protocol):
    def to_requests_proxies(self) -> MutableMapping[str, str] | None: ...

    def serialize(self) -> str: ...

    # For unit tests
    def __eq__(self, o: object) -> bool: ...


class EnvironmentProxyConfig:
    SERIALIZED = "FROM_ENVIRONMENT"

    def to_requests_proxies(self) -> None:
        return None

    def serialize(self) -> str:
        return self.SERIALIZED

    def __eq__(self, o: object) -> bool:
        return isinstance(o, EnvironmentProxyConfig)


class NoProxyConfig:
    SERIALIZED = "NO_PROXY"

    def to_requests_proxies(self) -> dict[str, str]:
        return {
            "http": "",
            "https": "",
        }

    def serialize(self) -> str:
        return self.SERIALIZED

    def __eq__(self, o: object) -> bool:
        return isinstance(o, NoProxyConfig)


class ExplicitProxyConfig:
    def __init__(self, url: str) -> None:
        self._url = url

    def to_requests_proxies(self) -> dict[str, str]:
        return {
            "http": self._url,
            "https": self._url,
        }

    def serialize(self) -> str:
        return self._url

    def __eq__(self, o: object) -> bool:
        return isinstance(o, ExplicitProxyConfig) and self._url == o._url


def deserialize_http_proxy_config(serialized_config: str | None) -> HTTPProxyConfig:
    """
    >>> deserialize_http_proxy_config("FROM_ENVIRONMENT") == EnvironmentProxyConfig()
    True
    >>> deserialize_http_proxy_config("NO_PROXY") == NoProxyConfig()
    True
    >>> deserialize_http_proxy_config("abc123") == ExplicitProxyConfig("abc123")
    True
    """
    if serialized_config is None:
        return EnvironmentProxyConfig()
    if serialized_config == EnvironmentProxyConfig.SERIALIZED:
        return EnvironmentProxyConfig()
    if serialized_config == NoProxyConfig.SERIALIZED:
        return NoProxyConfig()
    return ExplicitProxyConfig(serialized_config)


def http_proxy_config_from_user_setting(
    rulespec_value: tuple[str, str | None]
    | tuple[
        Literal["cmk_postprocessed"],
        Literal["environment_proxy", "no_proxy", "stored_proxy", "explicit_proxy"],
        str,
    ],
    http_proxies_global_settings: Mapping[str, Mapping[str, str]],
) -> HTTPProxyConfig:
    """Returns a proxy config object to be used for HTTP requests

    Intended to receive a value configured by the user using the HTTPProxyReference valuespec.
    """
    # For legacy compatibility
    if not isinstance(rulespec_value, tuple):
        return EnvironmentProxyConfig()

    match rulespec_value:
        case ("cmk_postprocessed", p_type, p_value):
            # FormSpec format
            assert p_type is not None
            proxy_type = {
                "stored_proxy": "global",
                "explicit_proxy": "url",
                "no_proxy": "no_proxy",
            }.get(p_type, "environment")
            value = p_value
        # Valuespec format
        case (p_type, p_value):
            assert len(rulespec_value) == 2
            proxy_type, value = rulespec_value

    if proxy_type == "environment":
        return EnvironmentProxyConfig()

    if (
        proxy_type == "global"
        and (
            global_proxy := http_proxies_global_settings.get(
                str(value),
                {},
            ).get(
                "proxy_url",
                None,
            )
        )
        is not None
    ):
        return ExplicitProxyConfig(global_proxy)

    if proxy_type == "url":
        return ExplicitProxyConfig(str(value))

    if proxy_type == "no_proxy":
        return NoProxyConfig()

    return EnvironmentProxyConfig()
