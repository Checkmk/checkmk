#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel

from cmk.config_generation.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    get_secret_from_params,
    HostConfig,
    HTTPProxy,
    IPAddressFamily,
    Secret,
)

from .utils import SecretType


class Mode(Enum):
    URL = "url"
    CERT = "cert"


class Family(Enum):
    enforce_ipv4 = "ipv4_enforced"  # -4
    enforce_ipv6 = "ipv6"  # -6
    allow_either = "ipv4"  # no argument


@dataclass(frozen=True)
class HostSettings:
    port: int | None
    family: Family | None
    virtual: str | None

    @classmethod
    def from_params(cls, params: Mapping[str, Any]) -> "HostSettings":
        family = params.get("address_family")
        return cls(
            port=params.get("port"),
            family=Family(family) if family is not None else None,
            virtual=params.get("virthost"),
        )

    def get_ip_address_family(self, host_config: HostConfig) -> Family:
        if self.family is not None:
            return self.family

        family = "ipv6" if host_config.ip_family == IPAddressFamily.IPv6 else "ipv4"
        return Family(family)

    def get_fallback_address(self, host_config: HostConfig) -> str:
        if self.get_ip_address_family(host_config) is Family.enforce_ipv6:
            return str(host_config.ipv6address)
        return str(host_config.ipv4address)


@dataclass(frozen=True)
class ProxySettings:
    address: str
    port: int | None
    auth: Secret | None

    @classmethod
    def from_params(cls, params: Mapping[str, Any]) -> "ProxySettings":
        auth: tuple[str, tuple[SecretType, str]] | None = params.get("auth")
        return cls(
            address=params["address"],
            port=params.get("port"),
            auth=get_secret_from_params(auth[1][0], auth[1][1], display_format="%s:%%s" % auth[0])
            if auth
            else None,
        )


@dataclass(frozen=True)
class DirectHost:
    address: str | None
    settings: HostSettings

    def get_server_address(self, host_config: HostConfig) -> str:
        if self.address is not None:
            return self.address

        return self.settings.get_fallback_address(host_config)

    @property
    def port(self) -> int | None:
        return self.settings.port

    def virtual_host(self, is_url_mode: bool, _host_config: HostConfig) -> str | None:
        return (
            self.settings.virtual
            if isinstance(self.settings.virtual, str)
            # In URL mode, don't return the address in this case, because check_http would
            # automatically set the HTTP Host header and use HTTP/1.1 instead of
            # HTTP/1.0. This can lead to request timeouts on hosts which are
            # not compliant with HTTP/1.1.
            else None
            if is_url_mode
            else self.address
        )


@dataclass(frozen=True)
class ProxyHost:
    proxy: ProxySettings
    settings: HostSettings

    def get_server_address(self, _host_config: HostConfig) -> str:
        return self.proxy.address

    @property
    def port(self) -> int | None:
        return self.proxy.port

    def virtual_host(self, _is_url_mode: bool, host_config: HostConfig) -> str:
        vhost = (
            self.settings.virtual
            if isinstance(self.settings.virtual, str)
            else self.settings.get_fallback_address(host_config)
        )
        return vhost if self.settings.port is None else f"{vhost}:{self.settings.port}"


class URLMode(BaseModel):
    uri: str | None = None
    ssl: str | None = None
    response_time: tuple[float, float] | None = None
    timeout: int | None = None
    user_agent: str | None = None
    add_headers: Sequence[str] = []
    auth: tuple[str, tuple[SecretType, str]] | None = None
    onredirect: Literal["ok", "warning", "critical", "follow", "sticky", "stickyport"] | None = None
    expect_response_header: str | None = None
    expect_response: Sequence[str] | None = None
    expect_string: str | None = None
    expect_regex: tuple[str, bool, bool, bool] | None = None
    post_data: tuple[str, str] | None = None
    method: Literal[
        "GET",
        "POST",
        "OPTIONS",
        "TRACE",
        "PUT",
        "DELETE",
        "HEAD",
        "CONNECT",
        "CONNECT:POST",
        "PROPFIND",
    ] | None = None
    no_body: bool = False
    page_size: tuple[int, int] | None = None
    max_age: int | None = None
    urlize: bool | None = None
    extended_perfdata: bool | None = None


class CertMode(BaseModel):
    cert_days: tuple[int, int]


@dataclass(frozen=True)
class HTTPParams:
    name: str
    host: DirectHost | ProxyHost
    mode: URLMode | CertMode
    disable_sni: bool = False


def _mode_from_params(params: Mapping[str, object]) -> URLMode | CertMode:
    mode_params = params["mode"]
    if not isinstance(mode_params, tuple):
        raise TypeError("Invalid parameters")

    mode_raw, mode_settings = mode_params
    mode = Mode(mode_raw)

    if mode is Mode.CERT:
        return CertMode.model_validate(mode_settings)

    return URLMode.model_validate(mode_settings)


def _host_from_params(params: Mapping[str, object]) -> DirectHost | ProxyHost:
    host_params = params.get("host", {})
    if not isinstance(host_params, dict):
        raise TypeError("Invalid parameters")

    settings = HostSettings.from_params(host_params)
    if address_settings := host_params.get("address"):
        address_type, address = address_settings
        return (
            DirectHost(
                address=address,
                settings=settings,
            )
            if address_type == "direct"
            else ProxyHost(
                proxy=ProxySettings.from_params(address),
                settings=settings,
            )
        )
    return DirectHost(
        address=None,
        settings=settings,
    )


def parse_http_params(params: Mapping[str, object]) -> HTTPParams:
    return HTTPParams(
        name=str(params["name"]),
        host=_host_from_params(params),
        mode=_mode_from_params(params),
        disable_sni=bool(params.get("disable_sni", False)),
    )


def _certificate_args(
    settings: CertMode,
    proxy_used: bool,
) -> list[str]:
    args: list[str] = []

    if settings.cert_days is not None:
        warn, crit = settings.cert_days
        args += ["-C", "%d,%d" % (warn, crit)]

    if proxy_used:
        args += ["--ssl", "-j", "CONNECT"]

    return args


def _url_args(  # pylint: disable=too-many-branches
    settings: URLMode,
    proxy_used: bool,
) -> Sequence[str | Secret]:
    args: list[str | Secret] = []

    if settings.uri is not None:
        args += ["-u", settings.uri]

    if settings.ssl == "auto":
        args.append("--ssl")
    elif settings.ssl is not None:
        args.append("--ssl=%s" % settings.ssl)

    if settings.response_time is not None:
        warn, crit = settings.response_time
        args += ["-w", "%f" % (warn / 1000.0), "-c", "%f" % (crit / 1000.0)]

    if settings.timeout is not None:
        args += ["-t", str(settings.timeout)]

    if settings.user_agent is not None:
        args += ["-A", settings.user_agent]

    for header in settings.add_headers:
        args += ["-k", header]

    if settings.auth is not None:
        username, password = settings.auth
        secret_type, secret_value = password
        args += [
            "-a",
            get_secret_from_params(secret_type, secret_value, display_format="%s:%%s" % username),
        ]

    if settings.onredirect is not None:
        args.append("--onredirect=%s" % settings.onredirect)

    if settings.expect_response is not None:
        args += ["-e", ",".join(settings.expect_response)]

    if settings.expect_string is not None:
        args += ["-s", settings.expect_string]

    if settings.expect_response_header is not None:
        args += ["-d", settings.expect_response_header]

    if settings.expect_regex is not None:
        if settings.expect_regex[3]:
            args.append("-l")
        if settings.expect_regex[1]:
            args.append("-R")
        else:
            args.append("-r")
        args += [settings.expect_regex[0]]
        if settings.expect_regex[2]:
            args.append("--invert-regex")

    if settings.extended_perfdata is not None:
        args.append("--extended-perfdata")

    if settings.post_data is not None:
        data, content_type = settings.post_data
        args += ["-P", data, "-T", content_type]

    if settings.method is not None or proxy_used:
        args += ["-j", settings.method or "CONNECT"]

    if settings.no_body:
        args.append("--no-body")

    if settings.page_size is not None:
        args += ["-m", "%d:%d" % settings.page_size]

    if settings.max_age is not None:
        args += ["-M", str(settings.max_age)]

    # FIXME: This option is deprecated. According to the monitoring-plugins
    # the "urlize" plugin should be used.
    if settings.urlize:
        args.append("-L")

    return args


def _common_args(params: HTTPParams, host_config: HostConfig) -> list[str | Secret]:
    args: list[str | Secret] = []

    ip_address_family = params.host.settings.get_ip_address_family(host_config)
    if ip_address_family is Family.enforce_ipv6:
        args.append("-6")
    if ip_address_family == Family.enforce_ipv4:
        args.append("-4")

    if not params.disable_sni:
        args.append("--sni")

    if isinstance(params.host, ProxyHost) and (proxy_auth := params.host.proxy.auth):
        args += ["-b", proxy_auth]

    if (specify_port := params.host.port) is not None:
        args += ["-p", "%s" % specify_port]

    args += ["-I", params.host.get_server_address(host_config)]

    is_url_mode = isinstance(params.mode, URLMode)
    if (virtual_host := params.host.virtual_host(is_url_mode, host_config)) is not None:
        args += ["-H", virtual_host]

    return args


def _get_http_description(params: HTTPParams) -> str:
    description = params.name
    if description.startswith("^"):
        return description[1:]

    # here we have to cover connection and certificate checks
    if (isinstance(params.mode, URLMode) and params.mode.ssl is not None) or isinstance(
        params.mode, CertMode
    ):
        return "HTTPS %s" % description
    return "HTTP %s" % description


def generate_http_command(
    params: HTTPParams, host_config: HostConfig, _http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[ActiveCheckCommand]:
    args: list[str | Secret] = []

    if isinstance(params.mode, CertMode):
        args += _certificate_args(
            params.mode,
            proxy_used=isinstance(
                params.host,
                ProxyHost,
            ),
        )
    else:
        args += _url_args(
            params.mode,
            proxy_used=isinstance(
                params.host,
                ProxyHost,
            ),
        )

    args += _common_args(params, host_config)
    yield ActiveCheckCommand(_get_http_description(params), args)


active_check_http = ActiveCheckConfig(
    name="http", parameter_parser=parse_http_params, commands_function=generate_http_command
)
