#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# See https://utcc.utoronto.ca/~cks/space/blog/linux/NFSStaleUnmounting
# Output changes from
# knvmsapprd:/transreorg/sap/trans /transreorg/sap/trans nfs4 rw,relatime,vers=4.0,rsize=1048576,wsize=1048576,namlen=255,hard,proto=tcp,timeo=600,retrans=2,sec=sys,clientaddr=172.24.98.63,local_lock=none,addr=172.24.98.57 0 0
# to
# knvmsapprd:/transreorg/sap/trans /transreorg/sap/trans\040(deleted) nfs4 rw,relatime,vers=4.0,rsize=1048576,wsize=1048576,namlen=255,hard,proto=tcp,timeo=600,retrans=2,sec=sys,clientaddr=172.24.98.63,local_lock=none,addr=172.24.98.57 0 0

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


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


def discovery_mounts(section: Mapping[str, Mount]) -> Iterable[tuple[str, Mapping]]:
    yield from (
        (m.mountpoint, {"expected_mount_options": m.options})
        for m in section.values()
        if m.fs_type != "tmpfs"
        and m.mountpoint not in ["/etc/resolv.conf", "/etc/hostname", "/etc/hosts"]
    )


def _should_ignore_option(option):
    for ignored_option in ["commit=", "localalloc=", "subvol=", "subvolid="]:
        if option.startswith(ignored_option):
            return True
    return False


def check_mounts(
    item: str, targetopts: Sequence[str], section: Mapping[str, Mount]
) -> Iterable[tuple[int, str]]:
    if (mount := section.get(item)) is None:
        return

    if mount.is_stale:
        yield 1, "Mount point detected as stale"
        return

    # Now compute the exact difference.
    exceeding = [
        opt for opt in mount.options if opt not in targetopts and not _should_ignore_option(opt)
    ]

    missing = [
        opt for opt in targetopts if opt not in mount.options and not _should_ignore_option(opt)
    ]

    if not missing and not exceeding:
        yield 0, "Mount options exactly as expected"
        return

    if missing:
        yield 1, "Missing: %s" % ",".join(missing)
    if exceeding:
        yield 1, "Exceeding: %s" % ",".join(exceeding)

    if "ro" in exceeding:
        yield 2, "Filesystem has switched to read-only and is probably corrupted"


check_info["mounts"] = LegacyCheckDefinition(
    service_name="Mount options of %s",
    parse_function=parse_mounts,
    discovery_function=discovery_mounts,  # type: ignore[typeddict-item]  # fix coming up
    check_function=check_mounts,
    check_ruleset_name="fs_mount_options",
    check_default_parameters={"expected_mount_options": []},  # will be overwritten by dicsovery
)
