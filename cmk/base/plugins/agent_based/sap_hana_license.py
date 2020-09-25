#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import namedtuple

from typing import Mapping

from .utils import sap_hana
from .agent_based_api.v1 import (
    render,
    check_levels,
    register,
    Service,
    Result,
    State as state,
)

from .agent_based_api.v1.type_defs import (
    AgentStringTable,
    DiscoveryResult,
    CheckResult,
    Parameters,
)

SAP_HANA_MAYBE = namedtuple("SAP_HANA_MAYBE", ["bool", "value"])


def parse_sap_hana_license(string_table: AgentStringTable) -> sap_hana.ParsedSection:
    section: sap_hana.ParsedSection = {}
    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        for line in lines:
            if len(line) < 7:
                continue

            inst = section.setdefault(sid_instance, {})
            for index, key, in [
                (0, "enforced"),
                (1, "permanent"),
                (2, "locked"),
                (5, "valid"),
            ]:
                value = line[index]
                inst[key] = SAP_HANA_MAYBE(_parse_maybe_bool(value), value)

            for index, key, in [
                (3, "size"),
                (4, "limit"),
            ]:
                try:
                    inst[key] = int(line[index])
                except ValueError:
                    pass
            inst["expiration_date"] = line[6]
    return section


register.agent_section(
    name="sap_hana_license",
    parse_function=parse_sap_hana_license,
)


def _parse_maybe_bool(value):
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return


def discovery_sap_hana_license(section: sap_hana.ParsedSection) -> DiscoveryResult:
    for elem in section:
        yield Service(item=elem)


def check_sap_hana_license(item: str, params: Parameters,
                           section: sap_hana.ParsedSection) -> CheckResult:

    data = section.get(item)
    if data is None:
        return

    enforced = data['enforced']
    if enforced.bool:
        yield from _check_product_usage(data['size'], data['limit'], params)
    elif enforced.bool is None:
        yield Result(state=state.UNKNOWN, summary="Status: unknown[%s]" % enforced.value)
    else:
        yield Result(state=state.OK, summary="Status: unlimited")

    permanent = data["permanent"]
    if permanent.bool:
        yield Result(state=state.OK, summary='License: %s' % permanent.value)
    else:
        yield Result(state=state.WARN, summary='License: not %s' % permanent.value)

    valid = data["valid"]
    if not valid.bool:
        yield Result(state=state.WARN, summary='not %s' % valid.value)

    expiration_date = data["expiration_date"]
    if expiration_date != "?":
        yield Result(state=state.WARN, summary='Expiration date: %s' % expiration_date)

    # It ONE physical device and at least two nodes.
    # Thus we only need to check the first one.
    return


def _check_product_usage(size, limit, params):
    yield from check_levels(size,
                            metric_name="license_size",
                            levels_upper=params.get('license_size'),
                            render_func=render.bytes,
                            label="Size")

    try:
        usage_perc = 100.0 * size / limit
    except ZeroDivisionError:
        yield Result(state=state.WARN, summary='Usage: cannot calculate')
    else:
        yield from check_levels(usage_perc,
                                metric_name="license_usage_perc",
                                levels_upper=params.get('license_usage_perc'),
                                render_func=render.percent,
                                label="Usage")


def cluster_check_sap_hana_license(item: str, params: Parameters,
                                   section: Mapping[str, sap_hana.ParsedSection]) -> CheckResult:
    yield Result(state=state.OK, summary='Nodes: %s' % ', '.join(section.keys()))
    for node_section in section.values():
        if item in node_section:
            yield from check_sap_hana_license(item, params, node_section)
            return


register.check_plugin(
    name="sap_hana_license",
    service_name="SAP HANA License %s",
    discovery_function=discovery_sap_hana_license,
    check_default_parameters={
        'license_usage_perc': (80.0, 90.0),
    },
    check_ruleset_name="sap_hana_license",
    check_function=check_sap_hana_license,
    cluster_check_function=cluster_check_sap_hana_license,
)
