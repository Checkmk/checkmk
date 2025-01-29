#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    RuleSetType,
    StringTable,
)
from cmk.plugins.lib.df import (
    df_check_filesystem_list,
    df_discovery,
    EXCLUDED_MOUNTPOINTS,
    FILESYSTEM_DEFAULT_PARAMS,
    FSBlock,
)

Section = Mapping[str, FSBlock]

# Example output from agent (sizes are in bytes). Note: the part
# [df] in this check is duplicated. We need this information because
# zfsget does not show pass-through filesystems like '/'. :-(

# <<<zfsget>>>
# bpool   name    bpool   -
# bpool   quota   0       default
# bpool   used    21947036798826  -
# bpool   available       11329512075414  -
# bpool   mountpoint      /bpool  default
# bpool   type    filesystem      -
# bpool/acs_fs    name    bpool/acs_fs    -
# bpool/acs_fs    quota   0       default
# bpool/acs_fs    used    4829131610      -
# bpool/acs_fs    available       11329512075414  -
# bpool/acs_fs    mountpoint      /backup/acs     local
# bpool/acs_fs    type    filesystem      -
# DataStorage/ ISO-File 	name	DataStorage/ ISO-File 	-
# DataStorage/ ISO-File 	quota	0	default
# DataStorage/ ISO-File 	used	180048	-
# DataStorage/ ISO-File 	available	3849844262352	-
# DataStorage/ ISO-File 	mountpoint	/mnt/DataStorage/ ISO-File 	default
# DataStorage/ ISO-File 	type	filesystem	-
# [df]
# /                    10255636 1836517 8419119    18%    /
# /dev                 10255636 1836517 8419119    18%    /dev
# proc                       0       0       0     0%    /proc
# ctfs                       0       0       0     0%    /system/contract
# mnttab                     0       0       0     0%    /etc/mnttab
# objfs                      0       0       0     0%    /system/object
# swap                 153480592     232 153480360     1%    /etc/svc/volatile
# /usr/lib/libc/libc_hwcap1.so.1 10255636 1836517 8419119    18%    /lib/libc.so.1
# fd                         0       0       0     0%    /dev/fd
# swap                 2097152   11064 2086088     1%    /tmp
# swap                 153480384      24 153480360     1%    /var/run
# tsrdb10exp/export    5128704      21 4982717     1%    /export
# tsrdb10exp/export/home 5128704      55 4982717     1%    /home
# tsrdb10exp/export/opt 5128704  145743 4982717     3%    /opt
# tsrdb10exp           5128704      21 4982717     1%    /tsrdb10exp
# tsrdb10dat           30707712 19914358 10789464    65%    /u01
# DataStorage/ ISO-File      3759613713     176 3759613537     0%    /mnt/DataStorage/ ISO-File


def _prep_value(value: str) -> str | float:
    """Try to convert string to float in MB"""
    try:
        return float(value) / (1024 * 1024)
    except ValueError:
        return value


def _get_similarity_of_strings(w1: str, w2: str) -> float:
    """
    Compares two strings and outputs a float value of the similarity match
    1.0 is a perfect match
    """
    return sum(i == j for i, j in zip(w1, w2)) / float(max(len(w1), len(w2)))


def _parse_zfs(lines: StringTable) -> Mapping[str, Mapping[str, str | float]]:
    """Go through all zfs lines and collect corresponding lines into a dict entry"""
    data: dict[str, dict[str, str | float]] = {}
    for line in lines:
        # last item is always the source element, we do not care about that one
        joined_line = " ".join(line[:-1])
        for prop in (" name ", " quota ", " used ", " available ", " mountpoint ", " type "):
            if prop not in joined_line:
                continue
            name, raw_value = joined_line.split(prop)
            if prop == " quota " and raw_value in ("0", "-"):
                continue

            data.setdefault(name, {})[prop.strip()] = _prep_value(raw_value)

    # parsed has the device name as key, because there may exist
    # several device names per mount point, and we know only
    # later which one to take
    parsed = {}
    for entry in data.values():
        mp = str(entry["mountpoint"])  # conversion just for mypy
        if mp.startswith("/"):
            e_name = str(entry["name"])  # conversion just for mypy
            entry["is_pool"] = "/" not in e_name
            if entry["type"] == "filesystem":
                parsed[e_name] = entry
    return parsed


def _parse_df(
    lines: StringTable,
    parsed_zfs: Mapping[str, Mapping[str, str | float]],
) -> Mapping[str, Mapping[str, str | float]]:
    parsed = {}
    for line in lines:
        line_str = " ".join(line)
        reg = r"(.+?)\s+(\d+)\s+(\d+)\s+(\d+)\W+(\d+[%])\s+(.*)"
        match = re.match(reg, line_str)
        if match:
            _first, kbytes, used, avail, _percent, mountpoint = match.groups()

            if mountpoint.startswith("/"):
                # here we get the actual device name
                # the output from 'df' does not give us a useful seperator(whitespace) but it is possible that:
                # a) the device name contains a whitespace
                # b) the fs_type is included
                # hence we can not get the device names easiliy
                # 'first' contians all elements from the beginning until the first kbytes item
                # we compare 'first' to zfs mountpoint names and take the device name with the highest similarity
                matches = []
                for name in parsed_zfs:
                    matches.append(_get_similarity_of_strings(name, _first))
                if matches and max(matches) > 0.5:
                    device = list(parsed_zfs)[matches.index(max(matches))]
                else:
                    # TODO: fix special case that will fail here if not zfs item exists
                    # white space in name and fs_type ("/foo", "bar", "zfs")
                    device = " ".join(_first)

                entry: dict[str, str | float] = {}
                entry["name"] = device
                entry["mountpoint"] = mountpoint
                # With some versions of solaris systems such as
                # solaris 10 10/08 s10s_u6wos_07b SPARC and solaris 10 10/09 s10x_u8wos_08a X86
                # there migth be a bug in the 'df -h' command which we use for filesystem infos.
                # Then the received data from the agent looks like "/ 0 12445007 19012273 5% /".
                # In this case we compute the total size as the sum of used and available.
                total = int(kbytes)
                used = int(used)
                avail = int(avail)
                if used and avail and not total:
                    total = used + avail
                else:
                    avail = total - used
                entry["total"] = total / 1024.0
                entry["used"] = used / 1024.0
                entry["available"] = avail / 1024.0
                parsed[mountpoint] = entry

    # Now remove duplicate entries for the root filesystem, such
    # as /dev/ or /lib/libc.so.1. We do this if size, used and
    # avail is equal. I hope that it will not happen too often
    # that this is per chance the case for different passed-through
    # filesystems
    root_entry = parsed.get("/")
    if root_entry:
        t_u_a = (root_entry["total"], root_entry["used"], root_entry["available"])
        drop = []
        for mountpoint, entry in parsed.items():
            if mountpoint != "/" and t_u_a == (entry["total"], entry["used"], entry["available"]):
                drop.append(mountpoint)
        for mp in drop:
            del parsed[mp]
    return parsed


def parse_zfsget(string_table: StringTable) -> Section:
    parsed = {}

    # check if a section for df exists and split info into two section lists
    if ["[df]"] in string_table:
        idx = string_table.index(["[df]"])
        info_zfs = string_table[:idx]
        info_df = string_table[idx + 1 :]
    else:
        info_zfs = string_table
        info_df = []

    # parse both lists of lines
    parsed_zfs = _parse_zfs(info_zfs)
    parsed_df = _parse_df(info_df, parsed_zfs)

    # parsed_df and parsed_final have the mount point as key
    for mountpoint, entry_df in parsed_df.items():
        # for every mount point in the df section, if the device name
        # is also present in the "parsed" variable, we take those data
        for name, entry_zfs in parsed_zfs.items():
            if entry_df["name"] == name:
                parsed[mountpoint] = entry_zfs
                break
        # if a mount point in the df section is not present in the
        # parsed variable, we take the data from the df section
        else:
            parsed[mountpoint] = entry_df

    return {
        mountpoint: (
            mountpoint,
            (
                float(entry["quota"])
                if "quota" in entry
                else (float(entry["used"]) + float(entry["available"]))
            ),
            float(entry["available"]),
            0.0,
        )
        for mountpoint, entry in parsed.items()
    }


agent_section_zfsget = AgentSection(
    name="zfsget",
    parse_function=parse_zfsget,
)


def discover_zfsget(params: Sequence[Mapping[str, Any]], section: Section) -> DiscoveryResult:
    yield from df_discovery(
        params,
        [mp for mp in section if mp not in EXCLUDED_MOUNTPOINTS],
    )


def check_zfsget(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=list(section.values()),
    )


check_plugin_zfsget = CheckPlugin(
    name="zfsget",
    service_name="Filesystem %s",
    discovery_function=discover_zfsget,
    discovery_default_parameters={"groups": []},
    discovery_ruleset_name="filesystem_groups",
    discovery_ruleset_type=RuleSetType.ALL,
    check_function=check_zfsget,
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
    check_ruleset_name="filesystem",
)
