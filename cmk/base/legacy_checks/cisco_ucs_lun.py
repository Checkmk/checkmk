#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree, StringTable
from cmk.base.check_legacy_includes.cisco_ucs import DETECT, MAP_OPERABILITY

check_info = {}

# comNET GmbH, Fabian Binder - 2018-05-07

# .1.3.6.1.4.1.9.9.719.1.45.8.1.14 cucsStorageLocalLunType
# .1.3.6.1.4.1.9.9.719.1.45.8.1.13 cucsStorageLocalLunSize
# .1.3.6.1.4.1.9.9.719.1.45.8.1.9  cucsStorageLocalLunOperability

map_luntype = {
    "0": (2, "unspecified"),
    "1": (1, "simple"),
    "2": (0, "mirror"),
    "3": (1, "stripe"),
    "4": (0, "lun"),
    "5": (0, "stripeParity"),
    "6": (0, "stripeDualParity"),
    "7": (0, "mirrorStripe"),
    "8": (0, "stripeParityStripe"),
    "9": (0, "stripeDualParityStripe"),
}


def discover_cisco_ucs_lun(info):
    return [(None, None)]


def check_cisco_ucs_lun(_no_item, _no_params, info):
    mode, size, status = info[0]
    state, state_readable = MAP_OPERABILITY.get(status, (3, "Unknown, status code %s" % status))
    mode_state, mode_state_readable = map_luntype.get(mode, (3, "Unknown, status code %s" % mode))
    # size is returned in MB
    # ^- or MiB? or what?
    size_readable = render.bytes(int(size or "0") * 1024 * 1024)
    yield state, "Status: %s" % state_readable
    yield 0, "Size: %s" % size_readable
    yield mode_state, "Mode: %s" % mode_state_readable


def parse_cisco_ucs_lun(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["cisco_ucs_lun"] = LegacyCheckDefinition(
    name="cisco_ucs_lun",
    parse_function=parse_cisco_ucs_lun,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.45.8.1",
        oids=["14", "13", "9"],
    ),
    service_name="LUN",
    discovery_function=discover_cisco_ucs_lun,
    check_function=check_cisco_ucs_lun,
)
