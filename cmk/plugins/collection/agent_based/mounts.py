#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# See https://utcc.utoronto.ca/~cks/space/blog/linux/NFSStaleUnmounting
# Output changes from
# knvmsapprd:/transreorg/sap/trans /transreorg/sap/trans nfs4 rw,relatime,vers=4.0,rsize=1048576,wsize=1048576,namlen=255,hard,proto=tcp,timeo=600,retrans=2,sec=sys,clientaddr=172.24.98.63,local_lock=none,addr=172.24.98.57 0 0
# to
# knvmsapprd:/transreorg/sap/trans /transreorg/sap/trans\040(deleted) nfs4 rw,relatime,vers=4.0,rsize=1048576,wsize=1048576,namlen=255,hard,proto=tcp,timeo=600,retrans=2,sec=sys,clientaddr=172.24.98.63,local_lock=none,addr=172.24.98.57 0 0

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

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


@dataclass(frozen=True, kw_only=True)
class Mount:
    mountpoint: str
    options: Sequence[str]  # this could be improved...
    fs_type: str
    is_stale: bool


def parse_mounts(string_table: StringTable) -> Mapping[str, Mount]:
    devices = set()
    section = {}
    for dev, mountpoint, fs_type, options, _dump, _fsck in string_table:
        if dev in devices:
            continue

        devices.add(dev)

        mountname = mountpoint.replace("\\040(deleted)", "")
        section[mountname] = Mount(
            mountpoint=mountname,
            options=sorted(options.split(",")),
            fs_type=fs_type,
            is_stale=mountpoint.endswith("\\040(deleted)"),
        )

    return section


def discovery_mounts(section: Mapping[str, Mount]) -> DiscoveryResult:
    yield from (
        Service(item=m.mountpoint, parameters={"expected_mount_options": m.options})
        for m in section.values()
        if m.fs_type != "tmpfs"
        and m.mountpoint not in ["/etc/resolv.conf", "/etc/hostname", "/etc/hosts"]
    )


def _should_ignore_option(option: str) -> bool:
    for ignored_option in ["commit=", "localalloc=", "subvol=", "subvolid="]:
        if option.startswith(ignored_option):
            return True
    return False


def check_mounts(item: str, params: Mapping[str, Any], section: Mapping[str, Mount]) -> CheckResult:
    if (mount := section.get(item)) is None:
        return

    if mount.is_stale:
        yield Result(state=State.WARN, summary="Mount point detected as stale")
        return

    targetopts = params["expected_mount_options"]

    # Now compute the exact difference.
    exceeding = [
        opt for opt in mount.options if opt not in targetopts and not _should_ignore_option(opt)
    ]

    missing = [
        opt for opt in targetopts if opt not in mount.options and not _should_ignore_option(opt)
    ]

    if not missing and not exceeding:
        yield Result(state=State.OK, summary="Mount options exactly as expected")
        return

    if missing:
        yield Result(state=State.WARN, summary="Missing: %s" % ",".join(missing))
    if exceeding:
        yield Result(state=State.WARN, summary="Exceeding: %s" % ",".join(exceeding))

    if "ro" in exceeding:
        yield Result(
            state=State.CRIT,
            summary="Filesystem has switched to read-only and is probably corrupted",
        )


agent_section_mounts = AgentSection(
    name="mounts",
    parse_function=parse_mounts,
)

check_plugin_mounts = CheckPlugin(
    name="mounts",
    service_name="Mount options of %s",
    discovery_function=discovery_mounts,
    check_function=check_mounts,
    check_ruleset_name="fs_mount_options",
    check_default_parameters={"expected_mount_options": []},
)
