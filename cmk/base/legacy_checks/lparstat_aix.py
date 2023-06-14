#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated,no-untyped-def"

from typing import Iterable

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util_unix, CPUInfo
from cmk.base.check_legacy_includes.transforms import transform_cpu_iowait
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.lparstat_aix import Section

# +------------------------------------------------------------------+
# | This file has been contributed and is copyrighted by:            |
# |                                                                  |
# | Joerg Linge 2009 <joerg.linge@pnp4nagios.org>     Copyright 2010 |
# +------------------------------------------------------------------+


def inventory_lparstat(section: Section) -> Iterable[tuple[None, dict]]:
    if section.get("util"):
        yield None, {}


def check_lparstat(_no_item, _no_params, section: Section):
    if section.get("update_required"):
        yield 3, "Please upgrade your AIX agent."
        return

    utilization = section.get("util", {})
    for name, (value, uom) in utilization.items():
        yield 0, "%s: %s%s" % (name.title(), value, uom), [(name, value)]


check_info["lparstat_aix"] = LegacyCheckDefinition(
    # section migrated already!
    check_function=check_lparstat,
    discovery_function=inventory_lparstat,
    service_name="lparstat",
)


def inventory_lparstat_aix_cpu(section: Section):
    if section.get("update_required"):
        return [(None, {})]
    if all(k in section.get("cpu", {}) for k in ("user", "sys", "wait", "idle")):
        return [(None, {})]
    return []


def check_lparstat_aix_cpu(_no_item, params, section: Section):
    if section.get("update_required"):
        yield 3, "Please upgrade your AIX agent."
        return

    cpu = section.get("cpu", {})
    user, system, wait = cpu.get("user"), cpu.get("sys"), cpu.get("wait")
    if user is None or system is None or wait is None:
        return

    # ancient legacy rule
    # and legacy None defaults before 1.6
    params = transform_cpu_iowait(params)

    values = CPUInfo("", user, 0, system, cpu.get("idle", 0), wait)

    for util_result in check_cpu_util_unix(values, params, values_counter=False):
        yield util_result

    try:
        cpu_entitlement = float(section["system_config"]["ent"])
        phys_cpu_consumption, _unit = section["util"]["physc"]
    except (KeyError, ValueError):
        return
    yield check_levels(
        phys_cpu_consumption,
        "cpu_entitlement_util",
        None,
        infoname="Physical CPU consumption",
        unit="CPUs",
    )
    yield check_levels(
        cpu_entitlement, "cpu_entitlement", None, infoname="Entitlement", unit="CPUs"
    )


check_info["lparstat_aix.cpu_util"] = LegacyCheckDefinition(
    # section migrated already!
    check_function=check_lparstat_aix_cpu,
    discovery_function=inventory_lparstat_aix_cpu,
    service_name="CPU utilization",
    check_ruleset_name="cpu_iowait",
)
