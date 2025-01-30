#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import re
import sys
from collections.abc import Mapping
from contextlib import suppress
from ipaddress import AddressValueError, IPv6Address, NetmaskValueError
from pprint import pprint
from typing import Literal

from pydantic import BaseModel, HttpUrl, ValidationError

from cmk.utils.redis import disable_redis

from cmk.gui.main_modules import load_plugins
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.rulesets import AllRulesets
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars


class HostType(enum.Enum):
    IPV6 = enum.auto()
    EMBEDDABLE = enum.auto()
    INVALID = enum.auto()


def _classify(host: str) -> HostType:
    with suppress(ValidationError):
        HttpUrl(url=f"http://{host}")
        return HostType.EMBEDDABLE
    with suppress(AddressValueError, NetmaskValueError):
        IPv6Address(host)
        return HostType.IPV6
    return HostType.INVALID


class V1Host(BaseModel, extra="forbid"):
    address: tuple[Literal["direct"], str]
    # "ipv4_enforced", "ipv6_enforced", "primary_enforced" don't have a counter part in V2.
    # "primary_enforced" has the additional issue, that the ssc would also need to support it.
    address_family: Literal["any", None] = None
    # If this field is unspecified, it will set depending on the `virtual host`, if check_cert is
    # true, if client_cert is true, client private key or -S is enabled. On redirect new ports might
    # be defined. This behaviour will not transfer to the new check, most likely.
    port: int | None = None
    # disallow any virtual host. This option is cannot be migrated, since we can't specify a
    # physical host.
    virthost: None = None


class V1Auth(BaseModel, extra="forbid"):
    user: str
    password: object


class V1Url(BaseModel, extra="forbid"):
    uri: str | None = None  # TODO: passed via -u in V1, unclear whether this is the same as V2.
    ssl: (
        Literal[
            "auto",  # use with auto-negotiation
            "ssl_1_2",  # enforce TLS 1.2
            "ssl_1_3",  # enforce TLS 1.3
            # "ssl_1",  # enforce TLS 1.0, not supported in V2
            # "ssl_2",  # enforce SSL 2.0, not supported in V2
            # "ssl_3",  # enforce SSL 3.0, not supported in V2
        ]
        | None
    ) = None
    response_time: tuple[float, float] | None = None
    timeout: int | None = None
    user_agent: str | None = None
    add_headers: list[str] | None = None
    auth: V1Auth | None = None
    onredirect: Literal["ok", "warning", "critical", "follow", "sticky", "stickyport"] | None = None
    expect_response_header: str | None = None
    expect_response: list[str] | None = None


class V1Value(BaseModel, extra="forbid"):
    name: str
    host: V1Host
    mode: tuple[Literal["url"], V1Url]


def _migratable(rule_value: Mapping[str, object]) -> bool:
    try:
        value = V1Value.model_validate(rule_value)
        if any(": " not in header for header in value.mode[1].add_headers or []):
            return False
        if value.mode[1].expect_response_header is not None:
            # TODO: Redirects behave differently in V1 and V2.
            return False
        type_ = _classify(value.host.address[1])
        if type_ is HostType.EMBEDDABLE:
            # This might have some issues, since customers can put a port, uri, and really mess with
            # us in a multitude of ways.
            return True
        return False
    except ValidationError:
        return False


def _migrate_header(header: str) -> dict[str, object]:
    name, value = header.split(": ", 1)
    return {"header_name": name, "header_value": value}


def _migrate_expect_response(response: list[str]) -> list[int]:
    result = []
    for item in response:
        if (status := re.search(r"\d{3}", item)) is not None:
            result.append(int(status.group()))
        else:
            raise ValueError(f"Invalid status code: {item}")
    return result


def _migrate(rule_value: V1Value) -> Mapping[str, object]:
    port = f":{rule_value.host.port}" if rule_value.host.port is not None else ""
    url_params = rule_value.mode[1]
    path = url_params.uri or ""
    match url_params.ssl:
        # In check_http.c (v1), this also determines the port.
        case None:
            scheme = "http"
            tls_versions = {}
        case "auto":
            scheme = "https"
            # TODO: PMs specified allow_higher False, revisit this, once we have their reasoning.
            tls_versions = {"tls_versions": {"min_version": "auto", "allow_higher": True}}
        case "ssl_1_2":
            scheme = "https"
            tls_versions = {"tls_versions": {"min_version": "tls_1_2", "allow_higher": False}}
        case "ssl_1_3":
            scheme = "https"
            tls_versions = {"tls_versions": {"min_version": "tls_1_3", "allow_higher": False}}
    match url_params.response_time:
        case None:
            response_time: Mapping[str, object] = {}
        case (warn_milli, crit_milli):
            response_time = {"response_time": ("fixed", (warn_milli / 1000, crit_milli / 1000))}
    match url_params.timeout:
        case None:
            timeout: Mapping[str, object] = {}
        case timeout_sec:
            timeout = {"timeout": float(timeout_sec)}
    match url_params.user_agent:
        case None:
            # TODO: This implicitly changes the user agent from `check_http/v2.3.3
            # (monitoring-plugins 2.3.3)` to `checkmk-active-httpv2/2.4.0`
            user_agent: Mapping[str, object] = {}
        case agent:
            user_agent = {"user_agent": agent}
    match url_params.add_headers:
        case None:
            add_headers: Mapping[str, object] = {}
        case headers:
            add_headers = {"add_headers": [_migrate_header(header) for header in headers]}
    match url_params.auth:
        case None:
            auth: Mapping[str, object] = {}
        case user_auth:
            auth = {"auth": ("user_auth", user_auth.model_dump())}
    match url_params.expect_response:
        case None:
            server_response: Mapping[str, object] = {}
        case expect_response:
            server_response = {
                "server_response": {"expected": _migrate_expect_response(expect_response)}
            }
    match url_params.onredirect:
        # TODO: V1 and V2 work differently, if searching for strings in documents, also need to test
        # with http codes.
        case None:
            redirects: Mapping[str, object] = {}
        case onredirect:
            redirects = {"redirects": onredirect}
    return {
        "endpoints": [
            {
                "service_name": {"prefix": "auto", "name": rule_value.name},
                # Risk: We can't be sure the active checks and the config cache use the same IP look
                # up (but both of them are based on the same user data. Moreover,
                # `primary_ip_config.address` (see `get_ssc_host_config` is slightly differently
                # implemented than `HOSTADDRESS` (see `attrs["address"]` in
                # `cmk/base/config.py:3454`).
                "url": f"{scheme}://{rule_value.host.address[1]}{port}{path}",
                "individual_settings": {
                    "connection": {
                        # TODO: revisit this, it might be inconsistent with V1
                        "method": ("get", None),
                        **tls_versions,
                        **timeout,
                        **user_agent,
                        **add_headers,
                        **auth,
                        **redirects,
                    },
                    **server_response,
                    **response_time,
                },
            }
        ],
    }


def main() -> None:
    load_plugins()
    with disable_redis(), gui_context(), SuperUserContext():
        set_global_vars()
        all_rulesets = AllRulesets.load_all_rulesets()
    for folder, rule_index, rule in all_rulesets.get_rulesets()["active_checks:http"].get_rules():
        if _migratable(rule.value):
            sys.stdout.write(f"MIGRATABLE: {folder}, {rule_index}\n")
        else:
            sys.stdout.write(f"IMPOSSIBLE: {folder}, {rule_index}\n")
        pprint(rule.value)  # nosemgrep: disallow-print
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
