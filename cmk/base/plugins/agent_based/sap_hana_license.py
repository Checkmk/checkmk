#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Mapping, NamedTuple, Optional, Union

from .agent_based_api.v1 import check_levels, IgnoreResultsError, register, render, Result, Service
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import sap_hana


class SAP_HANA_MAYBE(NamedTuple):
    bool: Optional[bool]
    value: Any


def parse_sap_hana_license(string_table: StringTable) -> sap_hana.ParsedSection:
    section: sap_hana.ParsedSection = {}
    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        inst: Dict[str, Union[int, SAP_HANA_MAYBE]] = {}
        for line in lines:
            if len(line) < 7:
                continue

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

        section.setdefault(sid_instance, inst)
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


def check_sap_hana_license(
    item: str, params: Mapping[str, Any], section: sap_hana.ParsedSection
) -> CheckResult:

    data = section.get(item)
    if not data:
        raise IgnoreResultsError("Login into database failed.")

    enforced = data["enforced"]
    if enforced.bool:
        yield from _check_product_usage(data["size"], data["limit"], params)
    elif enforced.bool is None:
        yield Result(state=state.UNKNOWN, summary="Status: unknown[%s]" % enforced.value)
    else:
        yield Result(state=state.OK, summary="Status: unlimited")

    permanent = data["permanent"]
    if permanent.bool:
        yield Result(state=state.OK, summary="License: %s" % permanent.value)
    else:
        yield Result(state=state.WARN, summary="License: not %s" % permanent.value)

    valid = data["valid"]
    if not valid.bool:
        yield Result(state=state.WARN, summary="not %s" % valid.value)

    expiration_date = data["expiration_date"]
    if expiration_date != "?":
        yield Result(state=state.WARN, summary="Expiration date: %s" % expiration_date)


def _check_product_usage(size, limit, params):
    yield from check_levels(
        size,
        metric_name="license_size",
        levels_upper=params.get("license_size"),
        render_func=render.bytes,
        label="Size",
    )

    try:
        usage_perc = 100.0 * size / limit
    except ZeroDivisionError:
        yield Result(state=state.WARN, summary="Usage: cannot calculate")
    else:
        yield from check_levels(
            usage_perc,
            metric_name="license_usage_perc",
            levels_upper=params.get("license_usage_perc"),
            render_func=render.percent,
            label="Usage",
        )


def cluster_check_sap_hana_license(
    item: str, params: Mapping[str, Any], section: Mapping[str, Optional[sap_hana.ParsedSection]]
) -> CheckResult:
    yield Result(state=state.OK, summary="Nodes: %s" % ", ".join(section.keys()))
    for node_section in section.values():
        if node_section is not None and item in node_section:
            yield from check_sap_hana_license(item, params, node_section)
            return


register.check_plugin(
    name="sap_hana_license",
    service_name="SAP HANA License %s",
    discovery_function=discovery_sap_hana_license,
    check_default_parameters={
        "license_usage_perc": (80.0, 90.0),
    },
    check_ruleset_name="sap_hana_license",
    check_function=check_sap_hana_license,
    cluster_check_function=cluster_check_sap_hana_license,
)
