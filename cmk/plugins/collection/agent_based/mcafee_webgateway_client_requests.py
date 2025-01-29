#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
The McAfee Web Gateway has been rebranded to Skyhigh Secure Web Gateway with its release 12.2.2.
Where possibile the "McAfee" string has been removed in favor of more generic therms.
The old plug-in names, value_store dict keys, and ruleset names have been kept for compatibility/history-keeping reasons.
"""

import time
import typing

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.mcafee_gateway import (
    compute_rate,
    DETECT_MCAFEE_WEBGATEWAY,
    DETECT_SKYHIGH_WEBGATEWAY,
    MISC_DEFAULT_PARAMS,
    MiscParams,
    ValueStore,
)


class Section(typing.NamedTuple):
    http: int | None = None
    httpv2: int | None = None
    https: int | None = None


def parse(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    http, httpv2, https = (int(x) if x.isdigit() else None for x in string_table[0])
    return Section(http=http, httpv2=httpv2, https=https)


snmp_section_mcafee_webgateway_client_requests = SimpleSNMPSection(
    name="mcafee_webgateway_client_requests",
    parsed_section_name="webgateway_client_requests",
    detect=DETECT_MCAFEE_WEBGATEWAY,
    parse_function=parse,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.7.2",
        oids=["2.1", "3.1", "6.1"],
    ),
)

snmp_section_skyhigh_security_webgateway_client_requests = SimpleSNMPSection(
    name="skyhigh_security_webgateway_client_requests",
    parsed_section_name="webgateway_client_requests",
    detect=DETECT_SKYHIGH_WEBGATEWAY,
    parse_function=parse,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.59732.2.7.2",
        oids=["2.1", "3.1", "6.1"],
    ),
)


def discovery_http(section: Section) -> DiscoveryResult:
    if section.http:
        yield Service()


def discovery_https(section: Section) -> DiscoveryResult:
    if section.https:
        yield Service()


def discovery_httpv2(section: Section) -> DiscoveryResult:
    if section.httpv2:
        yield Service()


def check_http(params: MiscParams, section: Section) -> CheckResult:
    yield from _check_http(time.time(), get_value_store(), params, section)


def check_https(params: MiscParams, section: Section) -> CheckResult:
    yield from _check_https(time.time(), get_value_store(), params, section)


def check_httpv2(params: MiscParams, section: Section) -> CheckResult:
    yield from _check_httpv2(time.time(), get_value_store(), params, section)


def _check_http(
    now: float, value_store: ValueStore, params: MiscParams, section: Section
) -> CheckResult:
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
) -> CheckResult:
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
) -> CheckResult:
    yield from compute_rate(
        now,
        value_store,
        section.httpv2,
        "requests_per_second",
        params["client_requests_httpv2"],
        "httpv2",
    )


check_plugin_mcafee_webgateway_http_client_requests = CheckPlugin(
    name="mcafee_webgateway_http_client_requests",
    sections=["webgateway_client_requests"],
    discovery_function=discovery_http,
    check_function=check_http,
    service_name="HTTP Client Request Rate",
    check_ruleset_name="mcafee_web_gateway_misc",
    check_default_parameters=MISC_DEFAULT_PARAMS,
)

check_plugin_mcafee_webgateway_https_client_requests = CheckPlugin(
    name="mcafee_webgateway_https_client_requests",
    sections=["webgateway_client_requests"],
    discovery_function=discovery_https,
    check_function=check_https,
    service_name="HTTPS Client Request Rate",
    check_ruleset_name="mcafee_web_gateway_misc",
    check_default_parameters=MISC_DEFAULT_PARAMS,
)

check_plugin_mcafee_webgateway_httpv2_client_requests = CheckPlugin(
    name="mcafee_webgateway_httpv2_client_requests",
    sections=["webgateway_client_requests"],
    discovery_function=discovery_httpv2,
    check_function=check_httpv2,
    service_name="HTTPv2 Client Request Rate",
    check_ruleset_name="mcafee_web_gateway_misc",
    check_default_parameters=MISC_DEFAULT_PARAMS,
)
