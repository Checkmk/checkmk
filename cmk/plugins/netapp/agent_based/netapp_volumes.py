#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# .1.3.6.1.4.1.789.1.5.8.1.1.1 = INTEGER: 1
# .1.3.6.1.4.1.789.1.5.8.1.1.2 = INTEGER: 2
# .1.3.6.1.4.1.789.1.5.8.1.1.3 = INTEGER: 3
# .1.3.6.1.4.1.789.1.5.8.1.2.1 = STRING: "vol0"
# .1.3.6.1.4.1.789.1.5.8.1.2.2 = STRING: "RvRBackup"
# .1.3.6.1.4.1.789.1.5.8.1.2.3 = STRING: "RundV"
# .1.3.6.1.4.1.789.1.5.8.1.3.1 = STRING: "67155442"
# .1.3.6.1.4.1.789.1.5.8.1.3.2 = STRING: "2600515058"
# .1.3.6.1.4.1.789.1.5.8.1.3.3 = STRING: "788575730"
# .1.3.6.1.4.1.789.1.5.8.1.4.1 = INTEGER: 1
# .1.3.6.1.4.1.789.1.5.8.1.4.2 = INTEGER: 1
# .1.3.6.1.4.1.789.1.5.8.1.4.3 = INTEGER: 1
# .1.3.6.1.4.1.789.1.5.8.1.5.1 = STRING: "online"
# .1.3.6.1.4.1.789.1.5.8.1.5.2 = STRING: "online"
# .1.3.6.1.4.1.789.1.5.8.1.5.3 = STRING: "online"
# .1.3.6.1.4.1.789.1.5.8.1.6.1 = STRING: "raid_dp"
# .1.3.6.1.4.1.789.1.5.8.1.6.2 = STRING: "raid_dp"
# .1.3.6.1.4.1.789.1.5.8.1.6.3 = STRING: "raid_dp"
# .1.3.6.1.4.1.789.1.5.8.1.7.1 = STRING: "root, diskroot, nosnap=off,
#  nosnapdir=off, minra=off, no_atime_update=off, raidtype=raid_dp, raidsize=16,
#  nvfail=off, snapmirrored=off, resyncsnaptime=60, create_ucode=off,
#  convert_ucode=off, maxdirsize=10485, fs_size_fixed=off, guarantee=volume,
#  svo_enable=off, svo_checksum=off, svo_allow_rman=off, svo_reject_errors=off,
#  no_i2p=off, fractional_reserve=100, extent=off, try_first=volume_grow"
# .1.3.6.1.4.1.789.1.5.8.1.7.2 = STRING: "nosnap=off, nosnapdir=off,
#  minra=off, no_atime_update=off, raidtype=raid_dp, raidsize=16, nvfail=off,
#  snapmirrored=off, resyncsnaptime=60, create_ucode=off, convert_ucode=off,
#  maxdirsize=10485, fs_size_fixed=off, guarantee=volume, svo_enable=off,
#  svo_checksum=off, svo_allow_rman=off, svo_reject_errors=off, no_i2p=off,
#  fractional_reserve=100, extent=off, try_first=volume_grow"
# .1.3.6.1.4.1.789.1.5.8.1.7.3 = STRING: "nosnap=on, nosnapdir=on,
#  minra=off, no_atime_update=off, raidtype=raid_dp, raidsize=16, nvfail=off,
#  snapmirrored=off, resyncsnaptime=60, create_ucode=off, convert_ucode=off,
#  maxdirsize=10485, fs_size_fixed=off, guarantee=volume, svo_enable=off,
#  svo_checksum=off, svo_allow_rman=off, svo_reject_errors=off, no_i2p=off,
#  fractional_reserve=100, extent=off, try_first=volume_grow"
# .1.3.6.1.4.1.789.1.5.8.1.8.1 = STRING: "1ddc9920-496e-11df-aae1-00a09800c998"
# .1.3.6.1.4.1.789.1.5.8.1.8.2 = STRING: "62ac1040-5a8d-11df-83fd-00a09800c998"
# .1.3.6.1.4.1.789.1.5.8.1.8.3 = STRING: "4edc66e0-d6a3-11df-8724-00a09800c998"
# .1.3.6.1.4.1.789.1.5.8.1.9.1 = STRING: "aggr0"
# .1.3.6.1.4.1.789.1.5.8.1.9.2 = STRING: "aggr0"
# .1.3.6.1.4.1.789.1.5.8.1.9.3 = STRING: "aggr0"
# .1.3.6.1.4.1.789.1.5.8.1.10.1 = INTEGER: 2
# .1.3.6.1.4.1.789.1.5.8.1.10.2 = INTEGER: 2
# .1.3.6.1.4.1.789.1.5.8.1.10.3 = INTEGER: 2
# .1.3.6.1.4.1.789.1.5.8.1.11.1 = INTEGER: 1
# .1.3.6.1.4.1.789.1.5.8.1.11.2 = INTEGER: 1
# .1.3.6.1.4.1.789.1.5.8.1.11.3 = INTEGER: 1
# .1.3.6.1.4.1.789.1.5.8.1.12.1 = ""
# .1.3.6.1.4.1.789.1.5.8.1.12.2 = ""
# .1.3.6.1.4.1.789.1.5.8.1.12.3 = ""
# .1.3.6.1.4.1.789.1.5.8.1.13.1 = ""
# .1.3.6.1.4.1.789.1.5.8.1.13.2 = ""
# .1.3.6.1.4.1.789.1.5.8.1.13.3 = ""


import dataclasses
from collections.abc import Mapping

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


@dataclasses.dataclass(frozen=True)
class NetappVolume:
    fsid: str
    owner: str
    state: str
    status: str


Section = Mapping[str, NetappVolume]

_NETAPP_VOLUMES_OWNER = {
    "1": "local",
    "2": "partner",
}


def parse_netapp_volumes(string_table: StringTable) -> Section:
    """
    >>> parse_netapp_volumes([["vol0", "23465813", "1", "online", "raid_dp, 64-bit, rlw_on"]])
    {'vol0': NetappVolume(fsid='23465813', owner='local', state='online', status='raid_dp, 64-bit, rlw_on')}
    """
    return {
        line[0]: NetappVolume(
            fsid=line[1],
            owner=_NETAPP_VOLUMES_OWNER.get(line[2], "UNKNOWN"),
            state=line[3],
            status=line[4],
        )
        for line in string_table
    }


snmp_section_netapp_volumes = SimpleSNMPSection(
    name="netapp_volumes",
    parse_function=parse_netapp_volumes,
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", "NetApp Release"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.789"),
    ),
    fetch=SNMPTree(
        ".1.3.6.1.4.1.789.1.5.8.1",
        [
            "2",  # volName
            "3",  # volFSID
            "4",  # volOwningHost
            "5",  # volState
            "6",  # volStatus
        ],
    ),
)


def discover(section: Section) -> DiscoveryResult:
    for volume_name, volume in section.items():
        if volume.owner == "local":
            yield Service(item=volume_name)


_VOLUME_STATUS_TO_MONITORING_STATUS = {
    "reconstructing": State.WARN,
    "normal": State.OK,
    "raid_dp": State.OK,
    "raid0": State.OK,
    "raid0, mirrored": State.OK,
    "raid4": State.OK,
    "mixed_raid_type": State.OK,
}


def check(
    item: str,
    section: Section,
) -> CheckResult:
    if (volume := section.get(item, None)) is None:
        return
    yield Result(
        state=State.OK,
        summary=f"FSID: {volume.fsid}, Owner: {volume.owner}",
    )
    yield Result(
        state=State.WARN if volume.state == "offline" else State.OK,
        summary=f"State: {volume.state}",
    )
    yield Result(
        state=_VOLUME_STATUS_TO_MONITORING_STATUS.get(
            volume.status.split(",", maxsplit=1)[0], State.CRIT
        ),
        summary=f"Status: {volume.status}",
    )


check_plugin_netapp_volumes = CheckPlugin(
    name="netapp_volumes",
    service_name="NetApp Vol %s",
    discovery_function=discover,
    check_function=check,
)
