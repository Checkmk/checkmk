#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# <<<tsm_drives>>>
# tsmfarm3   LIBRARY3           DRIVE01        LOADED             YES            000782XXXX
# tsmfarm3   LIBRARY3           DRIVE02        LOADED             YES            002348XXXX
# tsmfarm3   LIBRARY3           DRIVE03        EMPTY              YES            000783XXXX
# tsmfarm3   LIBRARY3           DRIVE04        EMPTY              NO            000784XXXX
# tsmfarm3   LIBRARY3           DRIVE05        LOADED             YES            000785XXXX

# <<<tsm_drives>>>
# default        GPFSFILE        GPFSFILE1       UNKNOWN YES
# default        GPFSFILE        GPFSFILE10      UNKNOWN YES
# default        GPFSFILE        GPFSFILE11      UNKNOWN YES
# default        GPFSFILE        GPFSFILE12      UNKNOWN YES
# default        GPFSFILE        GPFSFILE13      UNKNOWN YES

# Possible values for state:
# LOADED
# EMPTY
# UNAVAILABLE  -> crit
# UNLOADED
# RESERVED
# UNKNOWN      -> crit

# Possible values for loaded:
# YES          -> OK
# NO
# UNAVAILABLE_SINCE?
# POLLING?


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_tsm_drives(info):
    inventory = []
    for line in info:
        if len(line) == 6:
            inst, library, drive, _state, _online = line[:5]
            item = f"{library} / {drive}"
            if inst != "default":
                item = inst + " / " + item
            inventory.append((item, None))

    return inventory


def check_tsm_drives(item, params, info):
    for line in info:
        if len(line) >= 5:
            inst, library, drive, state, online = line[:5]
            libdev = f"{library} / {drive}"
            if item in {libdev, inst + " / " + libdev}:
                if len(line) >= 6:
                    serial = line[5]
                    infotext = "[%s] " % serial
                else:
                    serial = None
                    infotext = ""

                monstate = 0
                infotext += "state: %s" % state
                if state in ["UNAVAILABLE", "UNKNOWN"]:
                    monstate = 2
                    infotext += "(!!)"

                infotext += ", online: %s" % online
                if online != "YES":
                    monstate = 2
                    infotext += "(!!)"

                return (monstate, infotext)
    return (3, "drive not found")


def parse_tsm_drives(string_table: StringTable) -> StringTable:
    return string_table


check_info["tsm_drives"] = LegacyCheckDefinition(
    name="tsm_drives",
    parse_function=parse_tsm_drives,
    service_name="TSM Drive %s",
    discovery_function=discover_tsm_drives,
    check_function=check_tsm_drives,
)
