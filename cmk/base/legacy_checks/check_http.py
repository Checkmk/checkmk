#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from cmk.base.check_api import host_name, is_ipv6_primary, passwordstore_get_cmdline
from cmk.base.config import active_check_info


class Mode(Enum):
    URL = "url"
    CERT = "cert"


@dataclass(frozen=True)
class HostSettings:
    port: int | None
    family: str
    virtual: str | None

    @classmethod
    def from_params(cls, params: Mapping[str, Any]) -> "HostSettings":
        return cls(
            port=params.get("port"),
            family=params.get(
                "address_family",
                "ipv6" if is_ipv6_primary(host_name()) else "ipv4",
            ),
            virtual=params.get("virthost"),
        )

    @property
    def fallback_address(self) -> str:
        return "$_HOSTADDRESS_%s$" % self.family[-1]


@dataclass(frozen=True)
class ProxySettings:
    address: str
    port: int | None
    auth: str | tuple[str, str, str] | None

    @classmethod
    def from_params(cls, params: Mapping[str, Any]) -> "ProxySettings":
        return cls(
            address=params["address"],
            port=params.get("port"),
            auth=passwordstore_get_cmdline("%s:%%s" % auth[0], auth[1])
            if (auth := params.get("auth"))
            else None,
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
        return (
            self.settings.virtual
            if isinstance(self.settings.virtual, str)
            # In URL mode, don't return the address in this case, because check_http would
            # automatically set the HTTP Host header and use HTTP/1.1 instead of
            # HTTP/1.0. This can lead to request timeouts on hosts which are
            # not compliant with HTTP/1.1.
            else None
            if mode is Mode.URL
            else self.address
        )


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


def _host_from_params(params: Mapping[str, Any]) -> DirectHost | ProxyHost:
    settings = HostSettings.from_params(params)
    if address_settings := params.get("address"):
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
        address=settings.fallback_address,
        settings=settings,
    )


def _certificate_args(
    settings: Mapping[str, Any],
    proxy_used: bool,
) -> list[object]:
    args = []

    if "cert_days" in settings:
        # legacy behavior
        if isinstance(settings["cert_days"], int):
            args += ["-C", settings["cert_days"]]
        else:
            warn, crit = settings["cert_days"]
            args += ["-C", "%d,%d" % (warn, crit)]

    if proxy_used:
        args += ["--ssl", "-j", "CONNECT"]

    return args


def _url_args(  # pylint: disable=too-many-branches
    settings: Mapping[str, Any],
    proxy_used: bool,
) -> list[object]:
    args = []

    if "uri" in settings:
        args += ["-u", settings["uri"]]

    ssl = settings.get("ssl")
    if ssl in [True, "auto"]:
        args.append("--ssl")
    elif ssl:
        args.append("--ssl=%s" % ssl)

    if "response_time" in settings:
        warn, crit = settings["response_time"]
        args += ["-w", "%f" % (warn / 1000.0), "-c", "%f" % (crit / 1000.0)]

    if "timeout" in settings:
        args += ["-t", settings["timeout"]]

    if "user_agent" in settings:
        args += ["-A", settings["user_agent"]]

    for header in settings.get("add_headers", []):
        args += ["-k", header]

    if "auth" in settings:
        username, password = settings["auth"]
        args += ["-a", passwordstore_get_cmdline("%s:%%s" % username, password)]

    if "onredirect" in settings:
        args.append("--onredirect=%s" % settings["onredirect"])

    if "expect_response" in settings:
        args += ["-e", ",".join(settings["expect_response"])]

    if "expect_string" in settings:
        args += ["-s", settings["expect_string"]]

    if "expect_response_header" in settings:
        args += ["-d", settings["expect_response_header"]]

    if "expect_regex" in settings:
        if len(settings["expect_regex"]) >= 4 and settings["expect_regex"][3]:
            args.append("-l")
        if settings["expect_regex"][1]:
            args.append("-R")
        else:
            args.append("-r")
        args += [settings["expect_regex"][0]]
        if settings["expect_regex"][2]:
            args.append("--invert-regex")

    if settings.get("extended_perfdata"):
        args.append("--extended-perfdata")

    if "post_data" in settings:
        data, content_type = settings["post_data"]
        args += ["-P", data, "-T", content_type]

    if http_method := settings.get("method", "CONNECT" if proxy_used else None):
        args += ["-j", http_method]

    if settings.get("no_body"):
        args.append("--no-body")

    if "page_size" in settings:
        args += ["-m", "%d:%d" % settings["page_size"]]

    if "max_age" in settings:
        args += ["-M", settings["max_age"]]

    # FIXME: This option is deprecated. According to the monitoring-plugins
    # the "urlize" plugin should be used.
    if settings.get("urlize"):
        args.append("-L")

    return args


def _common_args(
    host: DirectHost | ProxyHost,
    mode: Mode,
    params: Mapping[str, Any],
) -> list[object]:
    args: list[object] = []

    if host.settings.family == "ipv6":
        args.append("-6")
    if not params.get("disable_sni"):
        args.append("--sni")
    if isinstance(host, ProxyHost) and (proxy_auth := host.proxy.auth):
        args += ["-b", proxy_auth]

    if (specify_port := host.port) is not None:
        args += ["-p", "%s" % specify_port]

    args += ["-I", host.server_address]
    if (virtual_host := host.virtual_host(mode)) is not None:
        args += ["-H", virtual_host]

    return args


def check_http_arguments(params: Mapping[str, Any]) -> list[object]:
    mode_raw, settings = params["mode"]
    mode = Mode(mode_raw)
    host = _host_from_params(params.get("host", {}))

    if mode is Mode.CERT:
        args = _certificate_args(
            settings,
            proxy_used=isinstance(
                host,
                ProxyHost,
            ),
        )
    else:
        args = _url_args(
            settings,
            proxy_used=isinstance(
                host,
                ProxyHost,
            ),
        )

    return args + _common_args(host, mode, params)


def check_http_description(params: Mapping[str, Any]) -> str:
    description = params["name"]
    if description.startswith("^"):
        return description[1:]

    mode_name, settings = params["mode"]
    # here we have to cover connection and certificate checks
    if settings.get("ssl") or mode_name == "cert":
        return "HTTPS %s" % description
    return "HTTP %s" % description


active_check_info["http"] = {
    "command_line": "check_http $ARG1$",
    "argument_function": check_http_arguments,
    "service_description": check_http_description,
}
