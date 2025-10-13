#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

# mypy: disable-error-code="possibly-undefined"

from collections.abc import Callable, Mapping
from typing import Literal

type _RulesetProxySpec = tuple[
    Literal["cmk_postprocessed"],
    Literal["environment_proxy", "no_proxy", "stored_proxy", "explicit_proxy"],
    str,
]


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


type HTTPProxyConfig = EnvironmentProxyConfig | NoProxyConfig | ExplicitProxyConfig


def deserialize_http_proxy_config(serialized_config: str | None) -> HTTPProxyConfig:
    """
    >>> deserialize_http_proxy_config("FROM_ENVIRONMENT") == EnvironmentProxyConfig()
    True
    >>> deserialize_http_proxy_config("NO_PROXY") == NoProxyConfig()
    True
    >>> deserialize_http_proxy_config("abc123") == ExplicitProxyConfig("abc123")
    True
    """
    match serialized_config:
        case None | EnvironmentProxyConfig.SERIALIZED:
            return EnvironmentProxyConfig()
        case NoProxyConfig.SERIALIZED:
            return NoProxyConfig()
        case str() as url:
            return ExplicitProxyConfig(url)
    raise ValueError(f"Invalid serialized proxy config: {serialized_config!r}")


def make_http_proxy_getter(
    http_proxies: Mapping[str, Mapping[str, str]],
) -> Callable[[tuple[str, str | None] | _RulesetProxySpec], HTTPProxyConfig]:
    def get_http_proxy(
        http_proxy: tuple[str, str | None] | _RulesetProxySpec,
    ) -> HTTPProxyConfig:
        """Returns a proxy config object to be used for HTTP requests

        Intended to receive a value configured by the user using the HTTPProxyReference valuespec.
        """
        return http_proxy_config_from_user_setting(
            http_proxy,
            http_proxies,
        )

    return get_http_proxy


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
