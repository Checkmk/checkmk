#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from contextlib import suppress
from typing import Any

from typing_extensions import TypedDict

from cmk.plugins.lib import multipath

from .agent_based_api.v1 import (
    check_levels,
    regex,
    register,
    render,
    Result,
    Service,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class _RawGroup(TypedDict):
    paths: list
    broken_paths: list
    luns: list
    uuid: str | None
    state: str | None
    numpaths: int
    device: str | None
    alias: str | None


def parse_multipath(  # pylint: disable=too-many-branches
    string_table: StringTable,
) -> multipath.Section:
    # New reported header lines need to be placed here
    # the matches need to be put in a list of tupples
    # while the structure of the tupple is:
    # 0: matching regex
    # 1: matched regex-group id of UUID
    # 2: matched regex-group id of alias (optional)
    # 3: matched regex-group id of dm-device (optional)
    reg_headers = [
        (regex(r"^[0-9a-z]{33}$"), 0, None, None),  # 1. (should be included in 3.)
        (regex(r"^([^\s]+)\s\(([^)]+)\)\s(dm.[0-9]+)"), 2, 1, 3),  # 2.
        (regex(r"^([^\s]+)\s\(([^)]+)\)"), 2, 1, None),  # 2.
        (regex(r"^[a-zA-Z0-9_]+$"), 0, None, None),  # 3.
        (regex(r"^([0-9a-z]{33}|[0-9a-z]{49})\s?(dm.[0-9]+).*$"), 1, None, 2),  # 4.
        (
            regex(r"^[a-zA-Z0-9_]+(dm-[0-9]+).*$"),
            0,
            None,
            1,
        ),  # 5. Remove this line in 1.2.0
        (regex(r"^([-.a-zA-Z0-9_ :]+)\s?(dm-[0-9]+).*$"), 1, None, 2),  # 6. and 7.
    ]

    reg_prio = regex(r"[\[ ]prio=")
    reg_lun = regex("[0-9]+:[0-9]+:[0-9]+:[0-9]+")
    uuid: str | None = None
    alias = None
    groups: dict[str, _RawGroup] = {}
    group: _RawGroup | dict = {}  # initial value will not be used
    numpaths = 0
    for line in string_table:
        # Ignore error messages due to invalid multipath.conf
        if line[0] == "multipath.conf":
            continue

        # newer agent also output the device mapper table.
        # ignore those lines for now.
        if line[0] == "dm":
            # Reset current device and skip line
            uuid = None
            continue

        # restore original non-split line
        l = " ".join(line)

        # Skip output when multipath is not present
        if (
            l.endswith("kernel driver not loaded")
            or l.endswith("does not exist, blacklisting all devices.")
            or l.endswith("A sample multipath.conf file is located at")
            or l.endswith("multipath.conf")
        ):
            uuid = None
            continue

        # First simply separate between data row and header row
        if line[0][0] not in ["[", "`", "|", "\\"] and not line[0].startswith("size="):
            # Try to match header lines
            matchobject = None
            for header_regex, uuid_pos, alias_pos, dm_pos in reg_headers:
                matchobject = header_regex.search(l)
                if matchobject:
                    uuid = matchobject.group(uuid_pos).strip()

                    if alias_pos:
                        alias = matchobject.group(alias_pos)
                    else:
                        alias = None

                    if dm_pos:
                        dm_device: str | None = matchobject.group(dm_pos)
                    else:
                        dm_device = None

                    break
            # No data row and no matching header row
            if not matchobject:
                continue

            # initialize information about next device
            numpaths = 0
            lun_info: list = []
            paths_info: list = []
            broken_paths: list = []
            group = {
                "paths": paths_info,
                "broken_paths": broken_paths,
                "luns": lun_info,
                "uuid": uuid,
                "state": None,
                "numpaths": 0,
                "device": dm_device,
                "alias": alias if alias else None,
            }
            if uuid is not None:
                groups[uuid] = group

            # Proceed with next line after init
            continue
        if uuid is not None:
            # Handle special syntax | |- 2:0:0:1 sda  ...
            if line[0] == "|":
                line = line[1:]
            if reg_prio.search(l):
                group["state"] = "".join(line[3:])
            elif len(line) >= 4 and reg_lun.match(line[1]):
                luninfo = f"{line[1]}({line[2]})"
                lun_info.append(luninfo)
                state = line[4]
                if "active" not in state:
                    broken_paths.append(luninfo)
                numpaths += 1
                group["numpaths"] = numpaths
                paths_info.append(line[2])

    return {uuid: multipath.Group(**raw_group) for uuid, raw_group in groups.items()}


register.agent_section(
    name="multipath",
    parse_function=parse_multipath,
)


# Get list of UUIDs of all multipath devices
# Length of UUID is 360a9800043346937686f456f59386741
def discover_multipath(params: Mapping[str, Any], section: multipath.Section) -> DiscoveryResult:
    for uuid, group in section.items():
        # take current number of paths as target value
        yield Service(
            item=group.alias if group.alias is not None and params.get("use_alias") else uuid,
            parameters={"levels": group.numpaths},
        )


# item is UUID (e.g. '360a9800043346937686f456f59386741') or alias (e.g. 'mpath0')
def _get_item_data(item: str, section: multipath.Section) -> multipath.Group | None:
    # Keys in section are the UUIDs.
    # First assume that we are looking for a UUID.
    with suppress(KeyError):
        return section[item]

    # Fall back to aliases
    for mmap in section.values():
        if mmap.alias == item:
            return mmap

    return None


def check_multipath(  # pylint: disable=too-many-branches
    item: str, params: Mapping[str, Any], section: multipath.Section
) -> CheckResult:
    if (mmap := _get_item_data(item, section)) is None:
        return

    # If the item is the alias, then show the UUID in the plug-in output.
    # If the item is the UUID, then vice versa.
    if item == mmap.uuid and mmap.alias:
        aliasinfo = "(%s): " % mmap.alias
    elif item == mmap.alias and mmap.uuid:
        aliasinfo = "(%s): " % mmap.uuid
    else:
        aliasinfo = ""

    all_paths = mmap.paths
    broken_paths = mmap.broken_paths
    num_paths = len(all_paths)
    num_broken = len(broken_paths)
    num_active = num_paths - num_broken

    levels = params.get("levels")

    yield from check_levels(
        num_active / num_paths * 100.0,
        levels_lower=(levels[0], levels[1]) if isinstance(levels, tuple) else None,
        render_func=render.percent,
        label=f"{aliasinfo}Paths active",
    )

    state = State.OK
    infotext = f"{num_active} of {num_paths}"
    if isinstance(levels, int):
        infotext += f" (expected: {levels})"
        if num_active < levels:
            state = State.CRIT
        elif num_active > levels:
            state = State.WARN
    yield Result(state=state, summary=infotext)

    if num_broken > 0:
        yield Result(state=State.CRIT, summary="Broken paths: %s" % ",".join(broken_paths))


register.check_plugin(
    name="multipath",
    service_name="Multipath %s",
    discovery_function=discover_multipath,
    discovery_ruleset_name="inventory_multipath_rules",
    discovery_default_parameters={"use_alias": False},
    check_function=check_multipath,
    check_ruleset_name="multipath",
    check_default_parameters={},
)
