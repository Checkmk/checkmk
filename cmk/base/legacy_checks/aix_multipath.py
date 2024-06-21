#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output:
# <<<aix_multipath>>>
# <<<aix_multipath>>>
# hdisk0 vscsi0 Available Enabled
# hdisk1 vscsi0 Available Enabled
# hdisk2 vscsi0 Available Enabled


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import StringTable


def inventory_aix_multipath(info):
    disks = {}
    for disk, _controller, _status in info:
        # filtering here to only see disks. there are other multipath devices,
        # too, but those have incomplete status => false positives
        if disk.startswith("hdisk"):
            disks[disk] = disks.get(disk, 0) + 1
    return [(disk, {"paths": p}) for disk, p in disks.items()]


def check_aix_multipath(item, params, info):
    path_count = 0
    state = 0
    message = []
    state_count = 0

    # Collecting all paths and there states
    for disk, _controller, status in info:
        if disk == item:
            path_count += 1
            if status != "Enabled":
                state_count += 1

    # How many Paths are not enabled
    if state_count != 0 and (100.0 / path_count * state_count) < 50:
        state = 1
        message.append("%d paths not enabled (!)" % (state_count))
    elif state_count != 0:
        state = 2
        message.append("%d paths not enabled (!!)" % (state_count))

    # Are some paths missing?
    path_message = "%d paths total" % path_count
    if path_count != params["paths"]:
        state = max(state, 1)
        message.append(path_message + " (should be: %d (!))" % (params["paths"]))
    else:
        message.append(path_message)

    return (state, ", ".join(message))


def parse_aix_multipath(string_table: StringTable) -> StringTable:
    return string_table


check_info["aix_multipath"] = LegacyCheckDefinition(
    parse_function=parse_aix_multipath,
    service_name="Multipath %s",
    discovery_function=inventory_aix_multipath,
    check_function=check_aix_multipath,
)
