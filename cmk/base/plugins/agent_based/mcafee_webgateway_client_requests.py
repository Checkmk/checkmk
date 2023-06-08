#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import typing

from cmk.base.plugins.agent_based.agent_based_api import v1
from cmk.base.plugins.agent_based.utils.mcafee_gateway import (
    compute_rate,
    DETECT_WEB_GATEWAY,
    MISC_DEFAULT_PARAMS,
    MiscParams,
    ValueStore,
)


class Section(typing.NamedTuple):
    http: int | None = None
    httpv2: int | None = None
    https: int | None = None


def parse(string_table: v1.type_defs.StringTable) -> Section | None:
    if not string_table:
        return None
    http, httpv2, https = [int(x) if x.isdigit() else None for x in string_table[0]]
    return Section(http=http, httpv2=httpv2, https=https)


v1.register.snmp_section(
    name="mcafee_webgateway_client_requests",
    detect=DETECT_WEB_GATEWAY,
    parse_function=parse,
    fetch=v1.SNMPTree(
        base=".1.3.6.1.4.1.1230.2.7.2",
        oids=["2.1", "3.1", "6.1"],
    ),
)


def discovery_http(section: Section) -> v1.type_defs.DiscoveryResult:
    if section.http:
        yield v1.Service()


def discovery_https(section: Section) -> v1.type_defs.DiscoveryResult:
    if section.https:
        yield v1.Service()


def discovery_httpv2(section: Section) -> v1.type_defs.DiscoveryResult:
    if section.httpv2:
        yield v1.Service()


def check_http(params: MiscParams, section: Section) -> v1.type_defs.CheckResult:
    yield from _check_http(time.time(), v1.get_value_store(), params, section)


def check_https(params: MiscParams, section: Section) -> v1.type_defs.CheckResult:
    yield from _check_https(time.time(), v1.get_value_store(), params, section)


def check_httpv2(params: MiscParams, section: Section) -> v1.type_defs.CheckResult:
    yield from _check_httpv2(time.time(), v1.get_value_store(), params, section)


def _check_http(
    now: float, value_store: ValueStore, params: MiscParams, section: Section
) -> v1.type_defs.CheckResult:
    yield from compute_rate(
        now,
        value_store,
        section.http,
        "requests_per_second",
        params["client_requests_http"],
        "http",
    )


def _check_https(
    now: float, value_store: ValueStore, params: MiscParams, section: Section
) -> v1.type_defs.CheckResult:
    yield from compute_rate(
        now,
        value_store,
        section.https,
        "requests_per_second",
        params["client_requests_https"],
        "https",
    )


def _check_httpv2(
    now: float, value_store: ValueStore, params: MiscParams, section: Section
) -> v1.type_defs.CheckResult:
    yield from compute_rate(
        now,
        value_store,
        section.httpv2,
        "requests_per_second",
        params["client_requests_httpv2"],
        "httpv2",
    )


v1.register.check_plugin(
    name="mcafee_webgateway_http_client_requests",
    sections=["mcafee_webgateway_client_requests"],
    discovery_function=discovery_http,
    check_function=check_http,
    service_name="HTTP Client Request Rate",
    check_ruleset_name="mcafee_web_gateway_misc",
    check_default_parameters=MISC_DEFAULT_PARAMS,
)

v1.register.check_plugin(
    name="mcafee_webgateway_https_client_requests",
    sections=["mcafee_webgateway_client_requests"],
    discovery_function=discovery_https,
    check_function=check_https,
    service_name="HTTPS Client Request Rate",
    check_ruleset_name="mcafee_web_gateway_misc",
    check_default_parameters=MISC_DEFAULT_PARAMS,
)

v1.register.check_plugin(
    name="mcafee_webgateway_httpv2_client_requests",
    sections=["mcafee_webgateway_client_requests"],
    discovery_function=discovery_httpv2,
    check_function=check_httpv2,
    service_name="HTTPv2 Client Request Rate",
    check_ruleset_name="mcafee_web_gateway_misc",
    check_default_parameters=MISC_DEFAULT_PARAMS,
)
