#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

from .agent_based_api.v1 import IgnoreResultsError, register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import sap_hana
from .utils.memory import check_element


def parse_sap_hana_memrate(string_table: StringTable) -> sap_hana.ParsedSection:
    section: sap_hana.ParsedSection = {}

    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        inst_data = {}
        for line in lines:
            if len(line) < 3 or line[0] != "mem_rate":
                continue

            for index, key in [(1, "used"), (2, "total")]:
                try:
                    inst_data[key] = int(line[index])
                except ValueError:
                    pass
        section.setdefault(sid_instance, inst_data)
    return section


register.agent_section(
    name="sap_hana_memrate",
    parse_function=parse_sap_hana_memrate,
)


def discovery_sap_hana_memrate(section: sap_hana.ParsedSection) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_sap_hana_memrate(
    item: str, params: Mapping[str, Any], section: sap_hana.ParsedSection
) -> CheckResult:
    data = section.get(item)
    if not data:
        raise IgnoreResultsError("Login into database failed.")

    yield from check_element(
        "Usage",
        data["used"],
        data["total"],
        params.get("levels", ("perc_used", (None, None))),
        metric_name="memory_used",
    )


register.check_plugin(
    name="sap_hana_memrate",
    service_name="SAP HANA Memory %s",
    discovery_function=discovery_sap_hana_memrate,
    check_function=check_sap_hana_memrate,
    check_ruleset_name="sap_hana_memory",
    check_default_parameters={"levels": ("perc_used", (70.0, 80.0))},
)
