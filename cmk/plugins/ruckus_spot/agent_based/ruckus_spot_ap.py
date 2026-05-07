#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping, Sequence
from typing import Any, Final, NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)


class _Device(NamedTuple):
    name: str
    status: int


Section = Mapping[str, Sequence[_Device]]


_BANDS_MAP: Final = {
    "1": "2.4 GHz",
    "2": "5 GHz",
}


def parse_ruckus_spot_ap(string_table: StringTable) -> Section:
    bands: dict[str, list[_Device]] = {}
    for band_info in json.loads(string_table[0][0]):
        band = _BANDS_MAP[str(band_info["band"])]
        bands.setdefault(band, []).extend(
            _Device(str(ap["name"]), int(ap["status"])) for ap in band_info["access_points"]
        )

    return bands


def discover_ruckus_spot_ap(section: Section) -> DiscoveryResult:
    yield from (Service(item=band) for band in section)


def check_ruckus_spot_ap(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    if not (devices := section.get(item)):
        return

    yield from check_levels_v1(
        len(devices),
        metric_name="ap_devices_total",
        render_func=lambda x: str(int(x)),
        label="Devices",
    )

    for label, ap_state, key in [
        ("drifted", 2, "levels_drifted"),
        ("not responding", 0, "levels_not_responding"),
    ]:
        yield from check_levels_v1(
            sum(dev.status == ap_state for dev in devices),
            metric_name="ap_devices_%s" % label.replace(" ", "_"),
            levels_upper=params.get(key),
            render_func=lambda x: str(int(x)),
            label=label.capitalize(),
            notice_only=True,
        )


agent_section_ruckus_spot_ap = AgentSection(
    name="ruckus_spot_ap",
    parse_function=parse_ruckus_spot_ap,
)


check_plugin_ruckus_spot_ap = CheckPlugin(
    name="ruckus_spot_ap",
    discovery_function=discover_ruckus_spot_ap,
    check_function=check_ruckus_spot_ap,
    check_default_parameters={},
    check_ruleset_name="ruckus_ap",
    service_name="Ruckus Spot Access Points %s",
)
