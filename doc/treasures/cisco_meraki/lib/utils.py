#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# enhancements by thl-cmk[at]outlook[dot]com, https://thl-cmk.hopto.org
# - changed check_last_reported_ts to output report as metric/levels
# - added levels_upper check_last_reported_ts
# - added section names from the cisco meraki special agent (for use in WATO)
# 2024-06-30: moved to cmk_addons/plugins/meraki/lib
#             renamed from cisco_meraki.py to utils.py
# 2025-03-30: moved to check APIv2
# 2025-06-24: fixed crash check_last_reported_ts (levels upper in old format)

import json
import time
from collections.abc import Mapping, Sequence
from typing import Final
from dataclasses import dataclass

from cmk.agent_based.v2 import (render, Result, State, check_levels, CheckResult, StringTable)
from cmk.rulesets.v1.form_specs import migrate_to_float_simple_levels

MerakiAPIData = Mapping[str, object]

# parameter names for agent options
SEC_NAME_ORGANISATIONS: Final = '_organisations'  # internal use runs always
SEC_NAME_DEVICE_INFO: Final = '_device_info'  # Not configurable, needed for piggyback
SEC_NAME_NETWORKS: Final = '_networks'  # internal use, runs always, needed for network names
SEC_NAME_ORG_API_REQUESTS: Final = 'api-requests-by-organization'  # internal use, runs always

SEC_NAME_APPLIANCE_UPLINKS: Final = 'appliance-uplinks'
SEC_NAME_APPLIANCE_UPLINKS_USAGE: Final = 'appliance-uplinks-usage'
SEC_NAME_APPLIANCE_VPNS: Final = 'appliance-vpns'
SEC_NAME_APPLIANCE_PERFORMANCE: Final = 'appliance-performance'
SEC_NAME_CELLULAR_UPLINKS: Final = 'cellular-uplinks'
SEC_NAME_DEVICE_STATUSES: Final = 'device-status'
SEC_NAME_DEVICE_UPLINKS_INFO: Final = 'device-uplinks-info'
SEC_NAME_LICENSES_OVERVIEW: Final = 'licenses-overview'
SEC_NAME_SENSOR_READINGS: Final = 'sensor-readings'
SEC_NAME_SWITCH_PORTS_STATUSES: Final = 'switch-ports-statuses'
SEC_NAME_WIRELESS_DEVICE_STATUS: Final = 'wireless-device-status'
SEC_NAME_WIRELESS_ETHERNET_STATUSES: Final = 'wireless-ethernet-statuses'
# SEC_NAME_DEVICE_LLDP_CDP: Final[str] = 'device-lldp-cdp'

# api cache defaults per section
SEC_CACHE_APPLIANCE_PERFORMANCE = 0
SEC_CACHE_APPLIANCE_UPLINKS_USAGE = 0
SEC_CACHE_APPLIANCE_UPLINKS = 60
SEC_CACHE_APPLIANCE_VPNS = 60
SEC_CACHE_CELLULAR_UPLINKS = 60
SEC_CACHE_DEVICE_INFO = 60
SEC_CACHE_DEVICE_STATUSES = 60
SEC_CACHE_DEVICE_UPLINKS_INFO = 60
SEC_CACHE_LICENSES_OVERVIEW = 600
SEC_CACHE_NETWORKS = 600
SEC_CACHE_ORG_API_REQUESTS = 0
SEC_CACHE_ORG_SWITCH_PORTS_STATUSES = 0
SEC_CACHE_ORGANISATIONS = 600
SEC_CACHE_SENSOR_READINGS = 0
SEC_CACHE_SWITCH_PORTS_STATUSES = 0
SEC_CACHE_WIRELESS_DEVICE_STATUS = 30
SEC_CACHE_WIRELESS_ETHERNET_STATUSES = 30

# Early Access
SEC_NAME_ORG_SWITCH_PORTS_STATUSES: Final = 'org-switch-ports-statuses'


@dataclass(frozen=True)
class MerakiNetwork:
    id: str  # 'N_24329156',
    name: str  # 'Main Office',
    product_types: Sequence[str]  # ['appliance', 'switch', 'wireless']
    time_zone: str  # 'America/Los_Angeles',
    tags: Sequence[str]  # [ 'tag1', 'tag2' ],
    enrollment_string: str | None  # 'my-enrollment-string',
    notes: str  # 'Additional description of the network',
    is_bound_to_config_template: bool  # false
    organisation_id: str
    organisation_name: str
    url: str


def load_json(string_table: StringTable) -> Sequence[MerakiAPIData]:
    try:
        return json.loads(string_table[0][0])
    except (IndexError, json.decoder.JSONDecodeError):
        return []


def check_last_reported_ts(
        last_reported_ts: float,
        levels_upper: Sequence[str, Sequence[float, float]] | Sequence[int, int] | None = None,
        as_metric: bool | None = True) -> CheckResult:

    if (age := time.time() - last_reported_ts) < 0:
        yield Result(
            state=State.OK,
            summary='Negative timespan since last report time.',
        )
        return
    if levels_upper and not levels_upper[0] == 'fixed':
        levels_upper = (levels_upper[0] * 3600, levels_upper[1] * 3600)
        levels_upper: Sequence[str, Sequence[float, float]]=migrate_to_float_simple_levels(levels_upper)

    yield from check_levels(
        value=age,
        label='Time since last report',
        metric_name='last_reported' if as_metric else None,
        levels_upper=levels_upper,
        render_func=render.timespan,
    )


def get_int(value: str | None) -> int | None:
    try:
        return int(value)
    except TypeError:
        return


def get_float(value: str | None) -> float | None:
    try:
        return float(value)
    except TypeError:
        return


def add_org_id_name_to_output(
        organisation_id: str,
        organisation_name: str,
        item_variant: str,
        dont_show_alias_on_info: bool,
) -> GeneratorExit:
    org_id = f'[{organisation_id}]'
    org_name = f'[{organisation_name}]'
    org_id_notice = f'Organisation ID: {organisation_id}'
    org_name_notice = f'Organisation name: {organisation_name}'

    match item_variant:
        case 'org_id':
            yield Result(state=State.OK, notice=org_id_notice)
            if dont_show_alias_on_info:
                yield Result(state=State.OK, notice=org_name_notice)
            else:
                yield Result(state=State.OK, summary=org_name, details=org_name_notice)
        case 'org_name':
            if dont_show_alias_on_info:
                yield Result(state=State.OK, notice=org_id_notice)
            else:
                yield Result(state=State.OK, summary=org_id, details=org_id_notice)
            yield Result(state=State.OK, notice=org_name_notice)

        case _:
            yield Result(state=State.OK, notice=org_id_notice)
            yield Result(state=State.OK, notice=org_name_notice)