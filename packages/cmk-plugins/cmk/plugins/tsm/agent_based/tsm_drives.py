#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


def parse_tsm_drives(string_table: StringTable) -> StringTable:
    return string_table


def discover_tsm_drives(section: StringTable) -> DiscoveryResult:
    for line in section:
        if len(line) == 6:
            inst, library, drive = line[0], line[1], line[2]
            item = f"{library} / {drive}"
            if inst != "default":
                item = f"{inst} / {item}"
            yield Service(item=item)


def check_tsm_drives(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if len(line) < 5:
            continue
        inst, library, drive, state, online = line[:5]
        libdev = f"{library} / {drive}"
        if item not in {libdev, f"{inst} / {libdev}"}:
            continue

        infotext = f"[{line[5]}] " if len(line) >= 6 else ""

        monstate = State.OK
        infotext += f"state: {state}"
        if state in ("UNAVAILABLE", "UNKNOWN"):
            monstate = State.CRIT
            infotext += "(!!)"

        infotext += f", online: {online}"
        if online != "YES":
            monstate = State.CRIT
            infotext += "(!!)"

        yield Result(state=monstate, summary=infotext)
        return

    yield Result(state=State.UNKNOWN, summary="drive not found")


agent_section_tsm_drives = AgentSection(
    name="tsm_drives",
    parse_function=parse_tsm_drives,
)


check_plugin_tsm_drives = CheckPlugin(
    name="tsm_drives",
    service_name="TSM Drive %s",
    discovery_function=discover_tsm_drives,
    check_function=check_tsm_drives,
)
