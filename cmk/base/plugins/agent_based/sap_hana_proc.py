#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

from .agent_based_api.v1 import IgnoreResultsError, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import sap_hana


def parse_sap_hana_proc(string_table: StringTable) -> sap_hana.ParsedSection:
    section: sap_hana.ParsedSection = {}

    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        for line in lines:
            if len(line) < 2:
                continue

            inst = section.setdefault(
                "%s - %s" % (sid_instance, line[1]),
                {
                    "port": line[0],
                    "pid": line[2],
                    "detail": line[3],
                    "acting": line[4],
                    "coordin": line[6],
                },
            )
            try:
                inst["sql_port"] = int(line[5])
            except ValueError:
                inst["sql_port"] = None
    return section


register.agent_section(
    name="sap_hana_proc",
    parse_function=parse_sap_hana_proc,
)


def discovery_sap_hana_proc(section: sap_hana.ParsedSection) -> DiscoveryResult:
    for sid_instance, data in section.items():
        yield Service(item=sid_instance, parameters={"coordin": data["coordin"]})


def check_sap_hana_proc(
    item: str, params: Mapping[str, Any], section: sap_hana.ParsedSection
) -> CheckResult:
    data = section.get(item)
    if data is None:
        raise IgnoreResultsError("Login into database failed.")

    yield Result(state=State.OK, summary="Port: %s, PID: %s" % (data["port"], data["pid"]))

    p_coordin = params["coordin"]
    coordin = data["coordin"]
    if p_coordin != coordin:
        yield Result(state=State.WARN, summary="Role: changed from %s to %s" % (p_coordin, coordin))
    elif coordin.lower() != "none":
        yield Result(state=State.OK, summary="Role: %s" % coordin)

    sql_port = data["sql_port"]
    if sql_port:
        yield Result(state=State.OK, summary="SQL-Port: %s" % sql_port)
    if data["acting"].lower() != "yes":
        yield Result(state=State.CRIT, summary="not acting")


register.check_plugin(
    name="sap_hana_proc",
    service_name="SAP HANA Process %s",
    discovery_function=discovery_sap_hana_proc,
    check_function=check_sap_hana_proc,
    check_ruleset_name="sap_hana_proc",
    check_default_parameters={},
)
