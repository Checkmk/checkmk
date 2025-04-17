#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<diskstat>>>
# 1300264105
#    8       0 sda 691860 951191 13559915 491748 234686 197346 3359512 94944 0 56844 586312
#    8      32 sdb 791860 91191 23589915 491748 234686 197346 3359512 94944 0 56844 586312

# Newer agent output also dm-* and Veritas devices and if
# available the following additional information for name rewriting:

# <<<diskstat>>>
# 1338931242
#    8       0 sda 6142 327 219612 2244 3190 6233 74075 8206 0 6523 10446
#  253       0 dm-0 4579 0 181754 2343 9249 0 73960 259491 0 1208 261833
#  253       1 dm-1 342 0 2736 47 3 0 11796464 5016 0 5063 5063
#  253       2 dm-2 160 0 1274 27 11 0 56 3 0 27 30
#    8      16 sdb 464 858 7717 336 1033 0 311454 3899 0 3007 4231
#    8      32 sdc 855 13352 106777 1172 915 0 154467 2798 0 3012 3967
#    8      48 sdd 1217 861 109802 1646 118 0 56151 1775 0 2736 3420
#    8      80 sdf 359 1244 58323 792 66 0 4793 388 0 765 1178
#    8      64 sde 310 1242 6964 268 118 0 56151 1607 0 1307 1872
#    8      96 sdg 1393 1242 314835 3759 129 0 56172 1867 0 4027 5619
#  199   27000 VxVM27000 131 0 990 61 11 0 21 29 0 89 90
#  199   27001 VxVM27001 0 0 0 0 0 0 0 0 0 0 0
# [dmsetup_info]
# vg_zwei-lv_home 253:2 vg_zwei lv_home
# vg_zwei-lv_swap 253:1 vg_zwei lv_swap
# vg_zwei-lv_root 253:0 vg_zwei lv_root
# [vx_dsk]
# c7 6978 /dev/vx/dsk/datadg/lalavol
# c7 6979 /dev/vx/dsk/datadg/oravol
# [device_wwn]
# wwn-0x60015ee0000b237f /dev/sda
# wwn-0x60015ee0000b237f-part2 dev/sda2
# wwn-0x60015ee0000b237f-part3 dev/sda3
# wwn-0x60015ee0000b237f-part1 dev/sda1
# wwn-0x60015ee0000b237f-part4 dev/sda4

# output may have zeros appended
#
# 8 0 sda 111918756 929875 3960367050 349083041 20142495 1149711 1021234448 851284769 0 233177192 1197549009 0 0 0 0
# 8 1 sda1 226 0 27481 3388 381 3 31472 35862 0 8123 39260 0 0 0 0
# 8 2 sda2 111918500 929875 3960337473 349079568 20142114 1149708 1021202976 851248906 0 233176504 1197492420 0 0 0 0
# 253 0 dm-0 883953 0 92124097 10287533 108572 0 2251672 809814 0 7545567 11097424 0 0 0 0
# 253 1 dm-1 21046 0 172072 157766 164020 0 1312160 29292970 0 124138 29451007 0 0 0 0
# 253 2 dm-2 750714 0 19747073 7702216 1445987 0 36811608 9817313 0 7159271 17520030 0 0 0 0

# Fields in /proc/diskstats
#  Index 0 -- major number
#  Index 1 -- minor number
#  Index 2 -- device name                        --> used by check
#  Index 3 -- # of reads issued
#  Index 4 -- # of reads merged
#  Index 5 -- # of sectors read (a 512 Byte)     --> used by check
#  Index 6 -- # of milliseconds spent reading
#  Index 7 -- # of writes completed
#  Index 8 -- # of writes merged
#  Index 9 -- # of sectors written (a 512 Byte)  --> used by check
#  Index 10 -- # of milliseconds spent writing
#  Index 11 -- # of I/Os currently in progress
#  Index 12 -- # of milliseconds spent doing I/Os
#  Index 13 -- weighted # of milliseconds spent doing I/Os

#  Kernel 4.18+ appends four more fields for discard
# 		tracking putting the total at 18:

#  Index 14 -- discards completed successfully
#  Index 15 -- discards merged
#  Index 16 -- sectors discarded
#  Index 17 -- time spent discarding

import re
import time
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from typing import Any, TypeVar

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    IgnoreResultsError,
    Result,
    RuleSetType,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib import diskstat, multipath


def parse_diskstat(string_table: StringTable) -> diskstat.Section:
    timestamp, proc_diskstat, name_info, wwn_info = diskstat_extract_name_info(string_table)
    assert timestamp is not None

    # Here we discover real partitions and exclude them:
    # Sort of partitions with disks - typical in XEN virtual setups.
    # Eg. there are xvda1, xvda2, but no xvda...
    device_names = [line[2] for line in proc_diskstat]
    real_partitions = {
        device_name
        for device_name in device_names
        if diskstat.DISKSTAT_DISKLESS_PATTERN.match(device_name)
        and re.sub("[0-9]+$", "", device_name) in device_names
    }

    disks = {}
    for line in proc_diskstat:
        if line[2] in real_partitions:
            continue

        try:
            (
                major,
                minor,
                device,
                read_ios,
                _read_merges,
                read_sectors,
                read_ticks,
                write_ios,
                _write_merges,
                write_sectors,
                write_ticks,
                ios_in_prog,
                total_ticks,
                _rq_ticks,
            ) = line
        except ValueError:
            # kernel 4.18+
            (
                major,
                minor,
                device,
                read_ios,
                _read_merges,
                read_sectors,
                read_ticks,
                write_ios,
                _write_merges,
                write_sectors,
                write_ticks,
                ios_in_prog,
                total_ticks,
                _rq_ticks,
                _discards_completed,
                _discards_merged,
                _sectors_discarded,
                _time_discard,
            ) = line

        if major != "None" and minor != "None" and (int(major), int(minor)) in name_info:
            device = name_info[(int(major), int(minor))]

        # service name will be either device or wwn
        # both are added to the section key to keep the diskstat.Disk type generic
        # across all disk plugins
        if (wwn := wwn_info.get(device)) is not None:
            device = f"{device}:{wwn}"

        # There are 1000 ticks per second
        disks[device] = {
            "timestamp": timestamp,
            "read_ticks": int(read_ticks) / 1000,
            "write_ticks": int(write_ticks) / 1000,
            "read_ios": int(read_ios),
            "write_ios": int(write_ios),
            "read_throughput": int(read_sectors) * 512,
            "write_throughput": int(write_sectors) * 512,
            "utilization": int(total_ticks) / 1000,  # not percent, but 0...1
            "queue_length": int(ios_in_prog),
        }

    return disks


# #  Index 0 -- major number
# #  Index 1 -- minor number
# #  Index 2 -- device name                        --> used by check
# #  Index 3 -- # of reads issued
# #  Index 4 -- # of reads merged
# #  Index 5 -- # of sectors read (a 512 Byte)     --> used by check
# #  Index 6 -- # of milliseconds spent reading
# #  Index 7 -- # of writes completed
# #  Index 8 -- # of writes merged
# #  Index 9 -- # of sectors written (a 512 Byte)  --> used by check
# #  Index 10 -- # of milliseconds spent writing
# #  Index 11 -- # of I/Os currently in progress
# #  Index 12 -- # of milliseconds spent doing I/Os
# #  Index 13 -- weighted # of milliseconds spent doing I/Os
#     for line in proc_diskstat:
#         node = line[0]
#
#
#
#     # For multipath devices use the entries for dm-?? and rename
#     # them with their multipath UUID/alias - and drop the according
#     # sdXY that belong to the paths.
#     multipath_name_info = {}
#     skipped_devices = set([])
#
#     # The generic function takes the following values per line:
#     #  0: None or node name
#     #  1: devname
#     #  2: read bytes counter
#     #  3: write bytes counter
#     # Optional ones:
#     #  4: number of reads
#     #  5: number of writes
#     #  6: timems
#     #  7: read queue length *counters*
#     #  8: write queue length *counters*
#     rewritten = [
#         ( l[0], # node name or None
#         diskstat_rewrite_device(name_info, multipath_name_info, l[0:4]),
#         int(l[6]),
#         int(l[10]),
#         int(l[4]),
#         int(l[8]),
#         # int(l[13])
#         ) for l in info[1:] if len(l) >= 14
#     ]
#
#     # Remove device mapper devices without a translated name
#     return [ line for line in rewritten
#              if not line[1].startswith("dm-")
#                 and not line[1] in skipped_devices ]


# Extra additional information from diskstat section about
# LVM and DM devices. These information is encapsulated
# with [dmsetup_info] and [vx_dsk] subsections. Example for
# name_info:
# {
#     (None, 253, 0): 'LVM vg00-rootvol',
#     (None, 253, 1): 'LVM vg00-tmpvol',
#     (None, 253, 2): 'LVM vg00-varvol',
#     (None, 253, 3): 'LVM vg00-optvol',
#     (None, 253, 4): 'LVM vg00-usrvol',
#     (None, 253, 5): 'LVM vg00-swapvol',
#     (None, 253, 6): 'LVM vgappl-applvol',
# }
def diskstat_extract_name_info(
    string_table: StringTable,
) -> tuple[int | None, StringTable, Mapping[tuple[int, int], str], Mapping[str, str]]:
    """Extract naming related information.

    Returns a 4-tuple:
    1) timestamp
    2) device info and metrics
    3) version to name mapping for LVM and DM devices
    4) WWN info (since device names aren't persistent, WWN should be used if available)

    """
    name_info = {}  # dict from (major, minor) to itemname
    wwn_info = {}  # dict from device name to WWN
    timestamp = None

    info_plain = []
    phase = "info"
    for line in string_table:
        match line[0]:
            case "[dmsetup_info]":
                phase = "dmsetup_info"
            case "[vx_dsk]":
                phase = "vx_dsk"
            case "[device_wwn]":
                phase = "device_wwn"
            case _:
                match phase:
                    case "info":
                        if len(line) == 1:
                            timestamp = int(line[0])
                        else:
                            info_plain.append(line[:14])
                    case "dmsetup_info":
                        try:
                            major, minor = map(int, line[1].split(":"))
                            if len(line) == 4:
                                name = "LVM %s" % line[0]
                            else:
                                name = "DM %s" % line[0]
                            name_info[major, minor] = name
                        except Exception:
                            pass  # ignore such crap as "No Devices Found"
                    case "vx_dsk":
                        major = int(line[0], 16)
                        minor = int(line[1], 16)
                        group, disk = line[2].split("/")[-2:]
                        name = f"VxVM {group}-{disk}"
                        name_info[major, minor] = name
                    case "device_wwn":
                        disk = line[1].split("/")[-1]
                        wwn = line[0].replace("wwn-", "").replace("nvme-eui.", "").lstrip("0")
                        wwn_info[disk] = wwn
    return timestamp, info_plain, name_info, wwn_info


agent_section_diskstat = AgentSection(
    name="diskstat",
    parse_function=parse_diskstat,
)


def diskstat_convert_info(
    section_diskstat: diskstat.Section,
    section_multipath: multipath.Section | None,
) -> diskstat.Section:
    converted_disks = dict(section_diskstat)  # we must not modify section_diskstat!

    # If we have information about multipathing, then remove the
    # physical path devices from the disks array. But only do this,
    # when there are information for the multipath device available.
    #
    # For multipath entries: Rename the generic names like "dm-8"
    # with multipath names like "SDataCoreSANsymphony_DAT07-fscl"
    if section_multipath:
        for uuid, group in section_multipath.items():
            if (
                group.device in converted_disks
                or group.alias is not None
                and f"DM {group.alias}" in converted_disks
            ):
                for path in group.paths:
                    if path in converted_disks:
                        del converted_disks[path]

            if group.device in converted_disks:
                converted_disks[uuid] = converted_disks[group.device]
                del converted_disks[group.device]

            if group.alias is not None and (alias := f"DM {group.alias}") in converted_disks:
                converted_disks[uuid] = converted_disks[alias]
                del converted_disks[alias]

    # Remove any left-over device mapper devices that are not part of a
    # known multipath device, LVM device or whatever
    for device in list(converted_disks):
        if device.startswith("dm-"):
            del converted_disks[device]

    return converted_disks


def _discovery_diskstat(
    params: Sequence[Mapping[str, Any]],
    section: Iterable[str],
) -> DiscoveryResult:
    item_candidates = list(section)
    # Skip over on empty data
    if not item_candidates:
        return

    modes = params[0]

    if modes["summary"]:
        yield Service(item="SUMMARY")

    for name in item_candidates:
        if (
            (physical := modes.get("physical"))
            and " " not in name
            and not diskstat.DISKSTAT_DISKLESS_PATTERN.match(name)
        ):
            if ":" in name:
                device, wwn = name.split(":")
                item = wwn if physical == "wwn" else device
                yield Service(item=item)
            else:
                yield Service(item=name)

        if modes["lvm"] and name.startswith("LVM "):
            yield Service(item=name)

        if modes["vxvm"] and name.startswith("VxVM "):
            yield Service(item=name)

        if modes["diskless"] and diskstat.DISKSTAT_DISKLESS_PATTERN.match(name):
            # Sort of partitions with disks - typical in XEN virtual setups.
            # Eg. there are xvda1, xvda2, but no xvda...
            yield Service(item=name)


def discover_diskstat(
    params: Sequence[Mapping[str, Any]],
    section_diskstat: diskstat.Section | diskstat.NoIOSection | None,
    section_multipath: multipath.Section | None,
) -> DiscoveryResult:
    match section_diskstat:
        case None:
            return
        case diskstat.NoIOSection():
            if params[0]["summary"]:
                yield Service(item="SUMMARY")
                return
        case _:
            yield from _discovery_diskstat(
                params,
                diskstat_convert_info(
                    section_diskstat,
                    section_multipath,
                ),
            )


def _compute_rates_single_disk(
    disk: diskstat.Disk,
    value_store: MutableMapping[str, Any],
    value_store_suffix: str = "",
) -> diskstat.Disk:
    raised_ignore_res_excpt = False
    disk_with_rates = {k: disk[k] for k in ("queue_length",) if k in disk}

    for metric in set(disk) - {"queue_length", "timestamp"}:
        try:
            disk_with_rates[metric] = get_rate(
                value_store,
                metric + value_store_suffix,
                disk["timestamp"],
                disk[metric],
                raise_overflow=True,
            )
        except IgnoreResultsError:
            raised_ignore_res_excpt = True

    if raised_ignore_res_excpt:
        raise IgnoreResultsError("Initializing counters")

    # statgrab_disk does not provide these
    if not all(k in disk for k in ("read_ticks", "read_ios", "utilization")):
        return disk_with_rates

    read_ticks_rate = disk_with_rates.pop("read_ticks")
    write_ticks_rate = disk_with_rates.pop("write_ticks")
    total_ios_rate = disk_with_rates["read_ios"] + disk_with_rates["write_ios"]
    total_bytes_rate = disk_with_rates["read_throughput"] + disk_with_rates["write_throughput"]

    # Some of the following computations were learned from Munin. Thanks
    # to that project!

    # The service time is computed from the utilization. If we work
    # e.g. 0.34 (34%) of the time and we can do 17 operations in that
    # time then the average latency is time * 0.34 / 17
    if total_ios_rate > 0:
        disk_with_rates["latency"] = disk_with_rates["utilization"] / total_ios_rate
        disk_with_rates["average_wait"] = (read_ticks_rate + write_ticks_rate) / total_ios_rate
        disk_with_rates["average_request_size"] = total_bytes_rate / total_ios_rate
    else:
        disk_with_rates["latency"] = 0.0
        disk_with_rates["average_wait"] = 0.0
        disk_with_rates["average_request_size"] = 0.0

    # Average read and write rate, from end to end, including queuing, etc.
    # and average size of one request
    if read_ticks_rate > 0 and disk_with_rates["read_ios"] > 0:
        disk_with_rates["average_read_wait"] = read_ticks_rate / disk_with_rates["read_ios"]
        disk_with_rates["average_read_request_size"] = (
            disk_with_rates["read_throughput"] / disk_with_rates["read_ios"]
        )
    else:
        disk_with_rates["average_read_wait"] = 0.0
        disk_with_rates["average_read_request_size"] = 0.0

    if write_ticks_rate > 0 and disk_with_rates["write_ios"] > 0:
        disk_with_rates["average_write_wait"] = write_ticks_rate / disk_with_rates["write_ios"]
        disk_with_rates["average_write_request_size"] = (
            disk_with_rates["write_throughput"] / disk_with_rates["write_ios"]
        )
    else:
        disk_with_rates["average_write_wait"] = 0.0
        disk_with_rates["average_write_request_size"] = 0.0

    return disk_with_rates


def check_diskstat(
    item: str,
    params: Mapping[str, Any],
    section_diskstat: diskstat.Section | diskstat.NoIOSection | None,
    section_multipath: multipath.Section | None,
) -> CheckResult:
    # Unfortunately, summarizing the disks does not commute with computing the rates for this check.
    # Therefore, we have to compute the rates first.
    if section_diskstat is None:
        return
    if isinstance(section_diskstat, diskstat.NoIOSection):
        raise IgnoreResultsError(section_diskstat.message)

    converted_disks = diskstat_convert_info(
        section_diskstat,
        section_multipath,
    )

    value_store = get_value_store()

    if item == "SUMMARY":
        names_and_disks_with_rates = diskstat.compute_rates_multiple_disks(
            converted_disks,
            value_store,
            _compute_rates_single_disk,
        )
        disk_with_rates = diskstat.summarize_disks(iter(names_and_disks_with_rates.items()))

    else:
        if not (disk_data := get_disk_for_item(item, converted_disks)):
            return

        disk_name, disk = disk_data
        disk_with_rates = _compute_rates_single_disk(
            disk,
            value_store,
        )

        if disk_name != item:
            yield Result(state=State.OK, summary=f"[{disk_name}]")

    yield from diskstat.check_diskstat_dict_legacy(
        params=params,
        disk=disk_with_rates,
        value_store=value_store,
        this_time=time.time(),
    )


def get_disk_for_item(
    item: str, converted_disks: diskstat.Section
) -> tuple[str, diskstat.Disk] | None:
    if disk := converted_disks.get(item):
        return item, disk

    for name, disk in converted_disks.items():
        if ":" in name:
            disk_name, wwn = name.split(":")
            if item in (disk_name, wwn):
                return disk_name, disk

    return None


_ItemData = TypeVar("_ItemData")


def _merge_cluster_sections(
    cluster_section: Mapping[str, Mapping[str, _ItemData] | None],
) -> Mapping[str, _ItemData] | None:
    return {
        k: v
        for section in cluster_section.values()
        if section is not None
        for k, v in section.items()
    } or None


def cluster_check_diskstat(
    item: str,
    params: Mapping[str, Any],
    section_diskstat: Mapping[str, diskstat.Section | None],
    section_multipath: Mapping[str, multipath.Section | None],
) -> CheckResult:
    yield from check_diskstat(
        item,
        params,
        _merge_cluster_sections(section_diskstat),
        _merge_cluster_sections(section_multipath),
    )


check_plugin_diskstat = CheckPlugin(
    name="diskstat",
    sections=["diskstat", "multipath"],
    service_name="Disk IO %s",
    discovery_ruleset_name="diskstat_inventory",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters=diskstat.DISKSTAT_DEFAULT_PARAMS,
    discovery_function=discover_diskstat,
    check_ruleset_name="diskstat",
    check_default_parameters={},
    check_function=check_diskstat,
    cluster_check_function=cluster_check_diskstat,
)
