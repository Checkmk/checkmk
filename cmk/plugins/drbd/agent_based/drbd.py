#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Author: Lars Michelsen <lm@mathias-kettner.de>

# Example outputs from agent:
#
# While syncing:
# <<<drbd>>>
# version: 8.3.8 (api:88/proto:86-94)
# GIT-hash: d78846e52224fd00562f7c225bcc25b2d422321d build by cssint@erzc20, 2010-06-17 14:47:26
#  0: cs:SyncSource ro:Primary/Secondary ds:UpToDate/Inconsistent C r----
#     ns:12031428 nr:0 dw:12031364 dr:1175992347 al:2179 bm:71877 lo:37 pe:0 ua:37 ap:0 ep:1 wo:b oos:301729988
#       [=======>............] sync'ed: 42.4% (294656/510908)M delay_probe: 145637
#       finish: 1:23:28 speed: 60,172 (51,448) K/sec
#
# Sync stalled:
# <<<drbd>>>
# b01srv05:~ # cat /proc/drbd
# version: 8.3.8 (api:88/proto:86-94)
# GIT-hash: d78846e52224fd00562f7c225bcc25b2d422321d build by cssint@erzc20, 2010-06-17 14:47:26
#  0: cs:SyncSource ro:Primary/Secondary ds:UpToDate/Inconsistent C r----
#     ns:11545876 nr:0 dw:11545900 dr:954551211 al:1955 bm:58360 lo:0 pe:0 ua:0 ap:0 ep:1 wo:b oos:523171100
#       [>....................] sync'ed:  0.1% (510908/510908)M delay_probe: 135599
#       stalled
#
# Synced:
# <<<drbd>>>
# version: 8.3.8 (api:88/proto:86-94)
# GIT-hash: d78846e52224fd00562f7c225bcc25b2d422321d build by cssint@erzc20, 2010-06-17 14:47:26
#  0: cs:Connected ro:Primary/Secondary ds:UpToDate/UpToDate C r----
#     ns:12227928 nr:0 dw:12227864 dr:1477722351 al:2300 bm:90294 lo:0 pe:0 ua:0 ap:0 ep:1 wo:b oos:0

# Description of the /proc/drbd output:
# http://www.drbd.org/users-guide/ch-admin.html#s-proc-drbd
#
# The information from /proc/drbd are grouped as followed (Extracted from doc above)
#
# General:
#   cs (connection state). Status of the network connection. See the section called
#               “Connection states” for details about the various connection states.
#    Available States:
#      StandAlone. No network configuration available. The resource has not yet been connected,
#                  or has been administratively disconnected (using drbdadm disconnect),
#                  or has dropped its connection due to failed authentication or split brain.
#      Disconnecting.  Temporary state during disconnection. The next state is StandAlone.
#      Unconnected.  Temporary state, prior to a connection attempt.
#                    Possible next states: WFConnection and WFReportParams.
#      Timeout. Temporary state following a timeout in the communication with the peer. Next state: Unconnected.
#      BrokenPipe. Temporary state after the connection to the peer was lost. Next state: Unconnected.
#      NetworkFailure. Temporary state after the connection to the partner was lost. Next state: Unconnected.
#      ProtocolError. Temporary state after the connection to the partner was lost. Next state: Unconnected.
#      TearDown. Temporary state. The peer is closing the connection. Next state: Unconnected.
#      WFConnection. This node is waiting until the peer node becomes visible on the network.
#      WFReportParams. TCP connection has been established, this node waits for the first network packet from the peer.
#      Connected. A DRBD connection has been established, data mirroring is now active. This is the normal state.
#      StartingSyncS. Full synchronization, initiated by the administrator, is just starting.
#                     The next possible states are: SyncSource or PausedSyncS.
#      StartingSyncT. Full synchronization, initiated by the administrator, is just starting. Next state: WFSyncUUID.
#      WFBitMapS. Partial synchronization is just starting. Next possible states: SyncSource or PausedSyncS.
#      WFBitMapT. Partial synchronization is just starting. Next possible state: WFSyncUUID.
#      WFSyncUUID. Synchronization is about to begin. Next possible states: SyncTarget or PausedSyncT.
#      SyncSource. Synchronization is currently running, with the local node being the source of synchronization.
#      SyncTarget. Synchronization is currently running, with the local node being the target of synchronization.
#      PausedSyncS. The local node is the source of an ongoing synchronization, but synchronization is currently paused.
#                   This may be due to a dependency on the completion of another synchronization process,
#                   or due to synchronization having been manually interrupted by drbdadm pause-sync.
#      PausedSyncT. The local node is the target of an ongoing synchronization, but synchronization
#                   is currently paused. This may be due to a dependency on the completion of another
#                   synchronization process, or due to synchronization having been manually interrupted by drbdadm pause-sync.
#      VerifyS. On-line device verification is currently running, with the local node being the source of verification.
#      VerifyT. On-line device verification is currently running, with the local node being the target of verification.
#
#   ro (roles). Roles of the nodes. The role of the local node is displayed first, followed by the role of the partner
#               node shown after the slash. See the section called “Resource roles” for details about the possible resource roles.
#    Available Roles:
#      Primary. The resource is currently in the primary role, and may be read from and written to.
#               This role only occurs on one of the two nodes, unless dual-primary node is enabled.
#      Secondary. The resource is currently in the secondary role. It normally receives updates
#                 from its peer (unless running in disconnected mode), but may neither be read from
#                 nor written to. This role may occur on one node or both nodes.
#      Unknown. The resource's role is currently unknown. The local resource role never has this status.
#               It is only displayed for the peer's resource role, and only in disconnected mode.
#
#   ds (disk states). State of the hard disks. Prior to the slash the state of the local node is displayed,
#                     after the slash the state of the hard disk of the partner node is shown.
#                     See the section called “Disk states” for details about the various disk states.
#    Disk States:
#      Diskless. No local block device has been assigned to the DRBD driver. This may mean that the resource
#                has never attached to its backing device, that it has been manually detached using drbdadm detach
#                or that it automatically detached after a lower-level I/O error.
#      Attaching. Transient state while reading meta data.
#      Failed. Transient state following an I/O failure report by the local block device. Next state: Diskless.
#      Negotiating. Transient state when an Attach is carried out on an already-connected DRBD device.
#      Inconsistent. The data is inconsistent. This status occurs immediately upon creation of a new resource,
#                    on both nodes (before the initial full sync). Also, this status is found in one node
#                    (the synchronization target) during synchronization.
#      Outdated. Resource data is consistent, but outdated.
#      DUnknown. This state is used for the peer disk if no network connection is available.
#      Consistent. Consistent data of a node without connection. When the connection
#                  is established, it is decided whether the data are UpToDate or Outdated.
#      UpToDate. Consistent, up-to-date state of the data. This is the normal state.
#
# Network:
#   ns (network send).  Volume of net data sent to the partner via the network connection; in Kibyte.
#   nr (network receive).  Volume of net data received by the partner via the network connection; in Kibyte.
# Disk:
#   dw (disk write). Net data written on local hard disk; in Kibyte.
#   dr (disk read). Net data read from local hard disk; in Kibyte.
# Stats:
#   al (activity log). Number of updates of the activity log area of the meta data.
#   bm (bit map).  Number of updates of the bitmap area of the meta data.
#   lo (local count). Number of open requests to the local I/O sub-system issued by DRBD.
#   pe (pending). Number of requests sent to the partner, but that have not yet been answered by the latter.
#   ua (unacknowledged). Number of requests received by the partner via the network connection, but that have not yet been answered.
#   ap (application pending). Number of block I/O requests forwarded to DRBD, but not yet answered by DRBD.
#   ep (epochs). Number of epoch objects. Usually 1. Might increase under I/O load
#                when using either the barrier or the none write ordering method. Since 8.2.7.
#   wo (write order). Currently used write ordering method: b (barrier), f (flush), d (drain) or n (none). Since 8.2.7.
#   oos (out of sync). Amount of storage currently out of sync; in Kibibytes. Since 8.2.6.


import re

# Default thresholds for drbd checks
import time
from collections.abc import Generator, Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels  # we can only use v2 after migrating the ruleset!
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

_drbd_block_start_match = re.compile("^[0-9]+:")

drbd_general_map = ["cs", "ro", "ds"]
drbd_net_map = ["cs", "ns", "nr"]
drbd_disk_map = ["cs", "dw", "dr"]
drbd_stats_map = ["cs", "al", "bm", "lo", "pe", "ua", "ap", "ep", "wo", "oos"]

drbd_cs_map = {
    "StandAlone": 1,
    "Disconnecting": 1,
    "Unconnected": 2,
    "Timeout": 2,
    "BrokenPipe": 2,
    "NetworkFailure": 2,
    "ProtocolError": 2,
    "TearDown": 2,
    "WFConnection": 2,
    "WFReportParams": 1,
    "Connected": 0,
    "Established": 0,
    "StartingSyncS": 1,
    "StartingSyncT": 1,
    "WFBitMapS": 1,
    "WFBitMapT": 1,
    "WFSyncUUID": 1,
    "SyncSource": 1,
    "SyncTarget": 1,
    "PausedSyncS": 1,
    "PausedSyncT": 1,
    "VerifyS": 0,
    "VerifyT": 0,
    "Ahead": 1,
    "Behind": 1,
}

drbd_ds_map = {
    "primary_Diskless": 2,
    "secondary_Diskless": 2,
    "primary_Attaching": 2,
    "secondary_Attaching": 2,
    "primary_Failed": 2,
    "secondary_Failed": 2,
    "primary_Negotiating": 2,
    "secondary_Negotiating": 2,
    "primary_Inconsistent": 1,
    "secondary_Inconsistent": 1,
    "primary_Outdated": 2,
    "secondary_Outdated": 2,
    "primary_DUnknown": 2,
    "secondary_DUnknown": 2,
    "primary_Consistent": 2,
    "secondary_Consistent": 2,
    "primary_UpToDate": 0,
    "secondary_UpToDate": 0,
    "unknown_DUnknown": 2,
}


def inventory_drbd(info, checktype):
    for line in info[2:]:
        if not _drbd_block_start_match.search(line[0]):
            continue
        parsed = drbd_parse_block(drbd_extract_block("drbd%s" % line[0][:-1], info), checktype)
        # Skip unconfigured drbd devices
        if parsed["cs"] == "Unconfigured":
            continue

        if checktype == "drbd":
            if "ro" not in parsed or "ds" not in parsed:
                continue
            levels = {
                "roles_inventory": parsed["ro"],
                "diskstates_inventory": parsed["ds"],
            }
        else:
            levels = {}

        yield "drbd%s" % line[0][:-1], levels


def drbd_parse_block(block, checktype):
    parsed = {}
    for line in block:
        for field in line:
            parts = field.split(":")
            if len(parts) > 1:
                # Only parse the requested information depending on the check
                # to be executed now
                if checktype == "drbd" and parts[0] in drbd_general_map:
                    if parts[0] in ["ro", "ds"]:
                        parsed[parts[0]] = parts[1].split("/")
                    else:
                        parsed[parts[0]] = parts[1]
                elif checktype == "drbd.net" and parts[0] in drbd_net_map:
                    parsed[parts[0]] = parts[1]
                elif checktype == "drbd.disk" and parts[0] in drbd_disk_map:
                    parsed[parts[0]] = parts[1]
                elif checktype == "drbd.stats" and parts[0] in drbd_stats_map:
                    parsed[parts[0]] = parts[1]

    return parsed


def drbd_extract_block(item, info):
    block = []
    inBlock = False
    # Ignore the first two lines since they contain drbd version information
    for line in info[2:]:
        if "drbd" + line[0][:-1] == item:
            inBlock = True
        elif inBlock and _drbd_block_start_match.search(line[0]) and "drbd" + line[0][:-1] != item:
            # Another block starts. So the requested block is finished
            break

        # Skip unwanted lines
        if not inBlock:
            continue

        # If this is reached we are in the wanted block
        block.append(line)

    return block


def drbd_get_block(item, info, checktype):
    block = drbd_extract_block(item, info)
    if len(block) > 0:
        return drbd_parse_block(block, checktype)
    return None


def get_roles_result(roles: tuple[str, str], params: Mapping[str, Any]) -> Result:
    output = "Roles: %s/%s" % roles
    current_roles = "_".join(str(role).lower() for role in roles)
    state = 0
    found_role_match = False

    if "roles" in params:
        if roles_params := params.get("roles"):
            for roles_entry, roles_state in roles_params:
                if roles_entry == current_roles:
                    found_role_match = True
                    state = max(state, roles_state)
                    break
        else:  # Ignore roles if set to None
            found_role_match = True

    if not found_role_match:
        if (roles_inventory := params.get("roles_inventory")) is not None:
            if roles != tuple(roles_inventory):
                state = max(2, state)
                output += " (Expected: %s/%s)" % tuple(roles_inventory)
        else:
            state = max(3, state)
            output += " (Check requires a new service discovery)"

    return Result(state=State(state), summary=output)


def get_diskstates_result(
    roles: tuple[str, str], diskstates: tuple[str, str], params: Mapping[str, Any]
) -> Result:
    output = "Diskstates: %s/%s" % tuple(diskstates)
    state = 0

    # Do not evaluate diskstates. Either set by rule or through the
    # legacy configuration option None in the check parameters tuple
    if (
        "diskstates" in params
        and params["diskstates"] is None
        or "diskstates_inventory" in params
        and params["diskstates_inventory"] is None
    ):
        return Result(state=State(state), summary=output)

    params_diskstates_dict = dict(params.get("diskstates", []))
    diskstates_info = set()

    for ro, ds in zip(roles, diskstates):
        diskstate = f"{ro.lower()}_{ds}"
        if (params_diskstate := params_diskstates_dict.get(diskstate)) is not None:
            state = max(state, params_diskstate)
            diskstates_info.add(f"{ro}/{ds}")
        else:
            default_state = drbd_ds_map.get(diskstate, 3)
            if default_state > 0:
                diskstates_info.add(f"{ro}/{ds}")
            state = max(state, drbd_ds_map.get(diskstate, 3))

    if diskstates_info:
        output += " (%s)" % ", ".join(diskstates_info)

    return Result(state=State(state), summary=output)


def check_drbd_general(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    if (parsed := drbd_get_block(item, section, "drbd")) is None:
        yield Result(state=State.UNKNOWN, summary="Undefined state")
        return
    if (cs := parsed["cs"]) == "Unconfigured":
        yield Result(state=State.CRIT, summary='The device is "Unconfigured"')
        return
    if cs not in drbd_cs_map:
        yield Result(state=State.UNKNOWN, summary='Undefined "connection state" in drbd output')
        return

    # Weight of connection state is calculated by the drbd_cs_map.
    # The roles and disk states are calculated using the expected values
    yield Result(state=State(drbd_cs_map[cs]), summary=f"Connection State: {cs}")

    roles = tuple(parsed["ro"])
    diskstates = tuple(parsed["ds"])

    yield get_roles_result(roles, params)
    yield get_diskstates_result(roles, diskstates, params)


def parse_drbd(string_table: StringTable) -> StringTable:
    return string_table


def discover_drbd(section: StringTable) -> DiscoveryResult:
    yield from [
        Service(item=item, parameters=parameters)
        for (item, parameters) in inventory_drbd(section, "drbd")
    ]


agent_section_drbd = AgentSection(name="drbd", parse_function=parse_drbd)
check_plugin_drbd = CheckPlugin(
    name="drbd",
    service_name="DRBD %s status",
    discovery_function=discover_drbd,
    check_function=check_drbd_general,
    check_ruleset_name="drbd",
    check_default_parameters={},
)


def drbd_net_levels(name: str, value: int) -> Generator[Result | Metric]:
    now = time.time()
    return check_levels(
        get_rate(get_value_store(), name, now, value, raise_overflow=True),
        metric_name=name,
        label=name.title(),
        render_func=render.networkbandwidth,
    )


def check_drbd_net(item: str, section: StringTable) -> CheckResult:
    if (parsed := drbd_get_block(item, section, "drbd.net")) is None:
        yield Result(state=State.UNKNOWN, summary="Undefined state")
        return
    if parsed["cs"] == "Unconfigured":
        yield Result(state=State.CRIT, summary='The device is "Unconfigured"')
        return

    yield from drbd_net_levels("in", int(parsed["nr"]))
    yield from drbd_net_levels("out", int(parsed["ns"]))


def discover_drbd_net(section: StringTable) -> DiscoveryResult:
    yield from [
        Service(item=item, parameters=parameters)
        for (item, parameters) in inventory_drbd(section, "drbd.net")
    ]


check_plugin_drbd_net = CheckPlugin(
    name="drbd_net",
    service_name="DRBD %s net",
    sections=["drbd"],
    discovery_function=discover_drbd_net,
    check_function=check_drbd_net,
    check_default_parameters=None,
)


def drbd_disk_levels(name: str, value: int) -> Generator[Result | Metric]:
    now = time.time()
    return check_levels(
        get_rate(get_value_store(), name, now, value, raise_overflow=True),
        metric_name=name,
        label=name.title(),
        render_func=render.iobandwidth,
    )


def check_drbd_disk(item: str, section: StringTable) -> CheckResult:
    if (parsed := drbd_get_block(item, section, "drbd.disk")) is None:
        yield Result(state=State.UNKNOWN, summary="Undefined state")
        return
    if parsed["cs"] == "Unconfigured":
        yield Result(state=State.CRIT, summary='The device is "Unconfigured"')
        return

    yield from drbd_disk_levels("write", int(parsed["dw"]))
    yield from drbd_disk_levels("read", int(parsed["dr"]))


def discover_drbd_disk(section: StringTable) -> DiscoveryResult:
    yield from [
        Service(item=item, parameters=parameters)
        for (item, parameters) in inventory_drbd(section, "drbd.disk")
    ]


check_plugin_drbd_disk = CheckPlugin(
    name="drbd_disk",
    service_name="DRBD %s disk",
    sections=["drbd"],
    discovery_function=discover_drbd_disk,
    check_function=check_drbd_disk,
    check_default_parameters=None,
)


def check_drbd_stats(item: str, section: StringTable) -> Generator[Result | Metric]:
    if (parsed := drbd_get_block(item, section, "drbd.stats")) is None:
        yield Result(state=State.UNKNOWN, summary="Undefined state")
        return
    if parsed["cs"] == "Unconfigured":
        yield Result(state=State.CRIT, summary='The device is "Unconfigured"')
        return

    def as_int(value: float) -> str:
        return f"{value:.0f}"

    for key, label in [
        ("al", "activity log updates"),
        ("bm", "bit map updates"),
        ("lo", "local count requests"),
        ("pe", "pending requests"),
        ("ua", "unacknowledged requests"),
        ("ap", "application pending requests"),
        ("ep", "epoch objects"),
        ("wo", "write order"),
        ("oos", "kb out of sync"),
    ]:
        try:
            value = int(parsed[key])
        except (KeyError, ValueError):
            value = 0

        metric_name = label.replace(" ", "_")

        yield from check_levels(value, metric_name=metric_name, label=label, render_func=as_int)


def discover_drbd_stats(section: StringTable) -> DiscoveryResult:
    yield from [
        Service(item=item, parameters=parameters)
        for (item, parameters) in inventory_drbd(section, "drbd.stats")
    ]


check_plugin_drbd_stats = CheckPlugin(
    name="drbd_stats",
    service_name="DRBD %s stats",
    sections=["drbd"],
    discovery_function=discover_drbd_stats,
    check_function=check_drbd_stats,
    check_default_parameters=None,
)
