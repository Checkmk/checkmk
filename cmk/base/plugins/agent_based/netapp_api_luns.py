#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Mapping, MutableMapping

from .agent_based_api.v1 import get_value_store, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import netapp_api
from .utils.df import (
    df_check_filesystem_single,
    FILESYSTEM_DEFAULT_LEVELS,
    MAGIC_FACTOR_DEFAULT_PARAMS,
    TREND_DEFAULT_PARAMS,
)

_MEBI = 1048576


# <<<netapp_api_luns:sep(9)>>>
# lun /vol/iscsi_crm_dblogs/crm_dblogs_lu01   read-only false size 644286182400   vserver ISCSI_CRM   size-used 538924421120  online true volume iscsi_crm_dblogs


def _netapp_api_luns_item(name: str, _values: object) -> str:
    return name.rsplit("/", 1)[-1]


def parse_netapp_api_luns(string_table: StringTable) -> netapp_api.SectionSingleInstance:
    return netapp_api.parse_netapp_api_single_instance(
        string_table, item_func=_netapp_api_luns_item
    )


register.agent_section(
    name="netapp_api_luns",
    parse_function=parse_netapp_api_luns,
)


def discover_netapp_api_luns(section: netapp_api.SectionSingleInstance) -> DiscoveryResult:
    yield from (Service(item=lun) for lun in section)


def check_netapp_api_luns(
    item: str,
    params: Mapping[str, Any],
    section: netapp_api.SectionSingleInstance,
) -> CheckResult:
    yield from _check_netapp_api_luns(item, params, section, get_value_store(), time.time())


def _check_netapp_api_luns(
    item: str,
    params: Mapping[str, Any],
    section: netapp_api.SectionSingleInstance,
    value_store: MutableMapping[str, Any],
    now: float,
) -> CheckResult:
    if (lun := section.get(item)) is None:
        return

    if lun.get("online") != "true":
        yield Result(state=State.CRIT, summary="LUN is offline")

    read_only = lun.get("read-only") == "true"
    if read_only != params.get("read_only"):
        expected = str(params.get("read_only")).lower()
        yield Result(
            state=State.WARN,
            summary="read-only is %s (expected: %s)" % (lun.get("read-only"), expected),
        )

    size_total_bytes = int(lun["size"])

    if params.get("ignore_levels"):
        yield Result(state=State.OK, summary=f"Total size: {render.bytes(size_total_bytes)}")
        yield Result(state=State.OK, summary="Used space is ignored")
    else:
        size_avail_bytes = size_total_bytes - int(lun["size-used"])
        yield from df_check_filesystem_single(
            value_store,
            item,
            # df_check_filesystem_single expects input in Megabytes
            # (mo: but we're passing mebibytes, apparently.)
            size_total_bytes / _MEBI,
            size_avail_bytes / _MEBI,
            0,
            None,
            None,
            params,
            this_time=now,
        )


register.check_plugin(
    name="netapp_api_luns",
    service_name="LUN %s",
    discovery_function=discover_netapp_api_luns,
    check_function=check_netapp_api_luns,
    check_ruleset_name="netapp_luns",
    check_default_parameters={
        **FILESYSTEM_DEFAULT_LEVELS,
        **MAGIC_FACTOR_DEFAULT_PARAMS,
        **TREND_DEFAULT_PARAMS,
        "read_only": False,
    },
)
