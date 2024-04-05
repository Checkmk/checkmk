#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, MutableMapping
from typing import Any

from cmk.plugins.lib import netapp_api
from cmk.plugins.lib.df import (
    FILESYSTEM_DEFAULT_LEVELS,
    MAGIC_FACTOR_DEFAULT_PARAMS,
    TREND_DEFAULT_PARAMS,
)

from .agent_based_api.v1 import get_value_store, register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

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

    size_total_bytes = int(lun["size"])
    size_avail_bytes = size_total_bytes - int(lun["size-used"])

    yield from netapp_api.check_netapp_luns(
        item=item,
        volume_name=lun["volume"],
        server_name=lun["vserver"],
        online=lun.get("online") == "true",
        read_only=lun.get("read-only") == "true",
        size_total_bytes=size_total_bytes,
        size_total=size_total_bytes / _MEBI,
        size_available=size_avail_bytes / _MEBI,
        now=now,
        value_store=value_store,
        params=params,
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
