#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from dataclasses import dataclass
from enum import auto, Enum
from typing import assert_never, Literal

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    IPAddressFamily,
    replace_macros,
    Secret,
)

FloatLevels = tuple[Literal["no_levels"], None] | tuple[Literal["fixed"], tuple[float, float]]


_SECONDS_PER_DAY = 3600 * 24


class RegexMode(BaseModel):
    regex: str
    case_insensitive: bool
    crit_if_found: bool
    multiline: bool


class PostData(BaseModel):
    data: str
    content_type: str


class PageSize(BaseModel):
    minimum: int
    maximum: int


class UserAuth(BaseModel):
    user: str
    password: Secret


class HttpModeUrlParams(BaseModel):
    uri: str | None = None
    ssl: str | None = None
    response_time: FloatLevels | None = None
    timeout: float | None = None
    user_agent: str | None = None
    add_headers: list[str] = Field(default_factory=list)
    auth: UserAuth | None = None
    onredirect: str | None = None
    expect_response_header: str | None = None
    expect_response: list[str] = Field(default_factory=list)
    expect_string: str | None = None
    expect_regex: RegexMode | None = None
    post_data: PostData | None = None
    method: str | None = None
    no_body: bool = Field(default=False)
    page_size: PageSize | None = None
    max_age: float | None = None
    urlize: bool = Field(default=False)
    extended_perfdata: bool = Field(default=False)


class HttpHostAddressProxyParams(BaseModel):
    address: str
    port: int | None = None
    auth: UserAuth | None = None


class HttpHostParams(BaseModel):
    address: (
        tuple[Literal["direct"], str] | tuple[Literal["proxy"], HttpHostAddressProxyParams] | None
    ) = None
    port: int | None = None
    address_family: Literal["any", "ipv4_enforced", "ipv6_enforced", "primary_enforced"] | None = (
        None
    )
    virthost: str | None = None


class HttpModeCertParams(BaseModel):
    cert_days: FloatLevels


class HttpParams(BaseModel):
    name: str
    host: HttpHostParams
    mode: tuple[Literal["url"], HttpModeUrlParams] | tuple[Literal["cert"], HttpModeCertParams]
    disable_sni: bool = Field(default=False)


class Mode(Enum):
    URL = "url"
    CERT = "cert"


class Family(Enum):
    ipv4 = auto()
    ipv6 = auto()
    any = auto()


def _parse_family(params: HttpHostParams, host_config: HostConfig) -> Family:
    match params.address_family:
        case "any" | None:  # Use any network address
            return Family.any
        case "ipv4_enforced":  # Enforce IPv4
            return Family.ipv4
        case "ipv6_enforced":  # Enforce IPv6
            return Family.ipv6
        case "primary_enforced":  # Enforce primary address family
            match host_config.primary_ip_config.family:
                case IPAddressFamily.IPV4:
                    return Family.ipv4
                case IPAddressFamily.IPV6:
                    return Family.ipv6


@dataclass(frozen=True)
class HostSettings:
    port: int | None
    family: Family
    virtual: str | None
    host_config: HostConfig

    @classmethod
    def from_params(cls, params: HttpHostParams, host_config: HostConfig) -> "HostSettings":
        return cls(
            port=params.port,
            family=_parse_family(params, host_config),
            virtual=params.virthost,
            host_config=host_config,
        )

    @property
    def fallback_address(self) -> str:
        match self.family:
            case Family.ipv4:
                if not self.host_config.ipv4_config:
                    raise ValueError("No IPv4 address configured")
                return self.host_config.ipv4_config.address
            case Family.ipv6:
                if not self.host_config.ipv6_config:
                    raise ValueError("No IPv6 address configured")
                return self.host_config.ipv6_config.address
            case Family.any:
                return self.host_config.primary_ip_config.address
            case _:
                assert_never(self.family)


@dataclass(frozen=True)
class ProxySettings:
    address: str
    port: int | None
    auth: UserAuth | None

    @classmethod
    def from_params(cls, params: HttpHostAddressProxyParams) -> "ProxySettings":
        return cls(
            address=params.address,
            port=params.port,
            auth=params.auth,
        )


@dataclass(frozen=True)
class DirectHost:
    address: str
    settings: HostSettings

    @property
    def server_address(self) -> str:
        return self.address

    @property
    def port(self) -> int | None:
        return self.settings.port

    def virtual_host(self, mode: Mode) -> str | None:
        if isinstance(self.settings.virtual, str):
            return self.settings.virtual
        # In URL mode, don't return the address, because check_http would automatically set the HTTP
        # Host header and use HTTP/1.1 instead of HTTP/1.0. This can lead to request timeouts on
        # hosts which are not compliant with HTTP/1.1.
        return None if mode is Mode.URL else self.address


@dataclass(frozen=True)
class ProxyHost:
    proxy: ProxySettings
    settings: HostSettings

    @property
    def server_address(self) -> str:
        return self.proxy.address

    @property
    def port(self) -> int | None:
        return self.proxy.port

    def virtual_host(self, mode: Mode) -> str:
        vhost = (
            self.settings.virtual
            if isinstance(self.settings.virtual, str)
            else self.settings.fallback_address
        )
        return vhost if self.settings.port is None else f"{vhost}:{self.settings.port}"


def _host_from_params(params: HttpHostParams, host_config: HostConfig) -> DirectHost | ProxyHost:
    settings = HostSettings.from_params(params, host_config)
    if (address_settings := params.address) is not None:
        match address_settings:
            case ("direct", str(address)):
                return DirectHost(address=address, settings=settings)
            case ("proxy", HttpHostAddressProxyParams() as address):
                return ProxyHost(proxy=ProxySettings.from_params(address), settings=settings)
    return DirectHost(
        address=settings.fallback_address,
        settings=settings,
    )


def _cert_arguments(
    host: DirectHost | ProxyHost, settings: HttpModeCertParams
) -> list[str | Secret]:
    args: list[str | Secret] = []
    match settings.cert_days:
        case ("fixed", (float(warn), float(crit))):
            args += ["-C", "%d,%d" % (int(warn / _SECONDS_PER_DAY), int(crit / _SECONDS_PER_DAY))]
    if isinstance(host, ProxyHost):
        args += ["--ssl", "-j", "CONNECT"]

    return args


def _expect_regex_arguments(expect_regex: RegexMode) -> list[str | Secret]:
    args: list[str | Secret] = []
    if expect_regex.multiline:
        args.append("-l")
    if expect_regex.case_insensitive:
        args.append("-R")
    else:
        args.append("-r")
    args += [expect_regex.regex]
    if expect_regex.crit_if_found:
        args.append("--invert-regex")
    return args


def _url_arguments(
    settings: HttpModeUrlParams,
    proxy_used: bool,
    host_config: HostConfig,
) -> list[str | Secret]:
    args: list[str | Secret] = []

    if (uri := settings.uri) is not None:
        args += ["-u", replace_macros(uri, host_config.macros)]

    match settings.ssl:
        case "auto":
            args.append("--ssl")
        case str(settings_ssl):
            ssl = {
                "ssl_1_1": "1.1",
                "ssl_1_2": "1.2",
                "ssl_1": "1",
                "ssl_2": "2",
                "ssl_3": "3",
            }[settings_ssl]
            args.append("--ssl=%s" % ssl)

    if (response_time := settings.response_time) is not None:
        match response_time:
            case ("fixed", (float(warn), float(crit))):
                args += ["-w", "%f" % warn, "-c", "%f" % crit]

    if (timeout := settings.timeout) is not None:
        args += ["-t", "%d" % timeout]

    if (user_agent := settings.user_agent) is not None:
        args += ["-A", user_agent]

    for header in settings.add_headers:
        args += ["-k", header]

    if (auth := settings.auth) is not None:
        args += ["-a", auth.password.unsafe("%s:%%s" % auth.user)]

    if (onredirect := settings.onredirect) is not None:
        args.append("--onredirect=%s" % onredirect)

    if len(settings.expect_response) > 0:
        args += ["-e", ",".join(settings.expect_response)]

    if (expect_string := settings.expect_string) is not None:
        args += ["-s", expect_string]

    if (expect_response_header := settings.expect_response_header) is not None:
        args += ["-d", expect_response_header]

    if (expect_regex := settings.expect_regex) is not None:
        args += _expect_regex_arguments(expect_regex)

    if settings.extended_perfdata:
        args.append("--extended-perfdata")

    if (post_data := settings.post_data) is not None:
        args += ["-P", post_data.data, "-T", post_data.content_type]

    http_method = "CONNECT" if proxy_used else None
    match settings.method:
        case None:
            pass
        case "CONNECT_POST":
            http_method = "CONNECT:POST"
        case _:
            http_method = settings.method
    if http_method:
        args += ["-j", http_method]

    if settings.no_body:
        args.append("--no-body")

    if (page_size := settings.page_size) is not None:
        args += ["-m", "%d:%d" % (page_size.minimum, page_size.maximum)]

    if (max_age := settings.max_age) is not None:
        args += ["-M", "%d" % max_age]

    # FIXME: This option is deprecated. According to the monitoring-plugins the "urlize" plug-in
    # should be used.
    if settings.urlize:
        args.append("-L")

    return args


def _common_args(
    host: DirectHost | ProxyHost,
    mode: Mode,
    params: HttpParams,
    host_config: HostConfig,
) -> list[str | Secret]:
    args: list[str | Secret] = []
    match host.settings.family:
        case Family.ipv4:
            args.append("-4")
        case Family.ipv6:
            args.append("-6")
    if not params.disable_sni:
        args.append("--sni")
    if isinstance(host, ProxyHost) and (proxy_auth := host.proxy.auth):
        args += ["-b", proxy_auth.password.unsafe("%s:%%s" % proxy_auth.user)]
    if (specify_port := host.port) is not None:
        args += ["-p", "%s" % specify_port]

    args += ["-I", replace_macros(host.server_address, host_config.macros)]
    if (virtual_host := host.virtual_host(mode)) is not None:
        args += ["-H", replace_macros(virtual_host, host_config.macros)]

    return args


def check_http_arguments(host_config: HostConfig, params: HttpParams) -> list[str | Secret]:
    host = _host_from_params(params.host, host_config)

    mode, settings = params.mode
    match (mode, settings):
        case ("cert", HttpModeCertParams() as cert_settings):
            args = _cert_arguments(host, cert_settings)
        case ("url", HttpModeUrlParams() as url_settings):
            args = _url_arguments(
                url_settings, proxy_used=isinstance(host, ProxyHost), host_config=host_config
            )
        case _:
            raise NotImplementedError(params.mode)
    return args + _common_args(host, Mode(mode), params, host_config)


def check_http_description(host_config: HostConfig, params: HttpParams) -> str:
    description = replace_macros(params.name, host_config.macros)
    if description.startswith("^"):
        return description[1:]

    mode_name, settings = params.mode
    # here we have to cover connection and certificate checks
    if (isinstance(settings, HttpModeUrlParams) and settings.ssl) or mode_name == "cert":
        return "HTTPS %s" % description
    return "HTTP %s" % description


def commands_function(params: HttpParams, host_config: HostConfig) -> Iterator[ActiveCheckCommand]:
    yield ActiveCheckCommand(
        service_description=check_http_description(host_config, params),
        command_arguments=check_http_arguments(host_config, params),
    )


active_check_http = ActiveCheckConfig(
    name="http", parameter_parser=HttpParams.model_validate, commands_function=commands_function
)
