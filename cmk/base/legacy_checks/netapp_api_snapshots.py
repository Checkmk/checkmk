#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

from cmk.base.check_api import get_bytes_human_readable, LegacyCheckDefinition
from cmk.base.check_legacy_includes.netapp_api import netapp_api_parse_lines
from cmk.base.config import check_info

# Agent output:
# <<<netapp_api_snapshots:sep(9)>>>
# volume_snapshot volch150    percent-reserved 22 blocks-reserved 3322    size-total 12122 ...
# volume_snapshot volch150    percentage-of-total-blocks 0 cumulative-total 122924 ...


def parse_netapp_api_snapshots(string_table):
    return netapp_api_parse_lines(string_table, custom_keys=["volume_snapshot"], as_dict_list=True)


def inventory_netapp_api_snapshots(parsed):
    for key in parsed:
        yield key, {}


def check_netapp_api_snapshots(item, params, parsed):
    data = parsed.get(item)

    if not data:
        return

    if data[0].get("state") != "online":
        yield 3, "No snapshot information available. Volume is %s" % data[0].get("state")
        return

    snapshot_total = int(data[0]["reserve-used-actual"]) * 1024.0
    size_total = int(data[0]["size-total"])
    reserved_bytes = int(data[0]["snapshot-blocks-reserved"]) * 1024.0

    if not reserved_bytes:
        yield 0, "Used snapshot space: %s" % get_bytes_human_readable(snapshot_total), [
            ("bytes", snapshot_total)
        ]
        yield params.get("state_noreserve", 1), "No snapshot reserve configured"
        return

    used_percent = snapshot_total / reserved_bytes * 100.0
    volume_total = size_total + reserved_bytes

    state = 0

    warn, crit = params.get("levels")
    if used_percent >= crit:
        state = 2
    elif used_percent >= warn:
        state = 1

    extra_info = ("(Levels at %d%%/%d%%)" % (warn, crit)) if state else ""

    yield state, "Reserve used: %.1f%% (%s)%s" % (
        used_percent,
        get_bytes_human_readable(snapshot_total),
        extra_info,
    )

    yield 0, "Total Reserve: %s%% (%s) of %s" % (
        data[0]["snapshot-percent-reserved"],
        get_bytes_human_readable(reserved_bytes),
        get_bytes_human_readable(volume_total),
    ), [("bytes", snapshot_total, 0, 0, 0, reserved_bytes)]


check_info["netapp_api_snapshots"] = LegacyCheckDefinition(
    parse_function=parse_netapp_api_snapshots,
    service_name="Snapshots Volume %s",
    discovery_function=inventory_netapp_api_snapshots,
    check_function=check_netapp_api_snapshots,
    check_ruleset_name="netapp_snapshots",
    check_default_parameters={"levels": (85.0, 90.0)},
)
