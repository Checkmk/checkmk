#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<mknotifyd:sep(0)>>>
# 1571151364
# [heute]
# Version:         2019.10.14
# Updated:         1571151346 (2019-10-15 16:55:46)
# Started:         1571143926 (2019-10-15 14:52:06, 7420 sec ago)
# Configuration:   1571143926 (2019-10-15 14:52:06, 7420 sec ago)
# Listening FD:    5
#
# Spool:           New
# Count:           0
# Oldest:
# Youngest:
#
# Spool:           Deferred
# Count:           0
# Oldest:
# Youngest:
#
# Spool:           Corrupted
# Count:           0
# Oldest:
# Youngest:
#
# Queue:           mail
# Waiting:         0
# Processing:      0
#
# Queue:           None
# Waiting:         0
# Processing:      0
#
# Connection:               127.0.0.1:49850
# Type:                     incoming
# State:                    established
# Since:                    1571143941 (2019-10-15 14:52:21, 7405 sec ago)
# Notifications Sent:       41
# Notifications Received:   41
# Pending Acknowledgements:
# Socket FD:                6
# HB. Interval:             10 sec
# LastIncomingData:         1571149829 (2019-10-15 16:30:29, 1517 sec ago)
# LastHeartbeat:            1571151344 (2019-10-15 16:55:44, 2 sec ago)
# InputBuffer:              0 Bytes
# OutputBuffer:             0 Bytes

from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)


@dataclass(frozen=True, kw_only=True)
class Spool:
    count: int
    oldest: int | None = None
    youngest: int | None = None


@dataclass(frozen=True, kw_only=True)
class Connection:
    type_: str
    state: str
    status_message: str | None = None
    since: int
    connect_time: float | None = None
    notifications_sent: int
    notifications_received: int


@dataclass(frozen=False, kw_only=True)
class Site:
    spools: dict[str, Spool]
    connections: dict[str, Connection]
    version: str | None = None
    updated: int | None = None


@dataclass(frozen=True, kw_only=True)
class MkNotifySection:
    sites: dict[str, Site]
    timestamp: float


class NoLineToParse(Exception):
    pass


def _get_varname_value(line: str) -> tuple[str, str]:

    if ":" not in line:
        raise NoLineToParse

    varname, value = line.split(":", 1)
    return varname, value.strip()


def _parse_site_data(
    starting_index: int, data: list[list[str]]
) -> tuple[int, str | None, int | None]:

    version: str | None
    updated: int | None
    try:
        _, version = _get_varname_value(data[starting_index + 1][0])
        _, value = _get_varname_value(data[starting_index + 2][0])
        updated = int(value.split()[0])
    except (NoLineToParse, IndexError):
        # spooler in error
        version = updated = None

    return starting_index + 2, version, updated


def _get_connection(index: int, data: list[list[str]]) -> tuple[int, Connection]:

    keys = [
        "Type",
        "State",
        "Status Message",
        "Since",
        "Connect Time",
        "Notifications Sent",
        "Notifications Received",
    ]

    connection_data: dict[str, str] = {}
    for key in keys:
        index += 1
        varname, value = _get_varname_value(data[index][0])
        # Status Message and  Connect Time are optional
        if varname != key:
            index -= 1
            continue
        connection_data[key.lower().replace(" ", "_")] = value

    connect_time = connection_data.get("connect_time")
    return index, Connection(
        type_=connection_data["type"],
        state=connection_data["state"],
        status_message=connection_data.get("status_message"),
        since=int(connection_data["since"].split()[0]),
        connect_time=(float(connect_time.split()[0]) if connect_time else None),
        notifications_sent=int(connection_data["notifications_sent"].split()[0]),
        notifications_received=int(connection_data["notifications_received"].split()[0]),
    )


def _get_spool(index: int, data: list[list[str]]) -> tuple[int, Spool]:

    def _split_parse_date(value: str) -> int | None:
        try:
            return int(value.split()[0])
        except (ValueError, IndexError):
            return None

    keys = ["Count", "Oldest", "Youngest"]

    spool_data: dict[str, str] = {}
    for key in keys:
        index += 1
        _, value = _get_varname_value(data[index][0])
        spool_data[key.lower()] = value

    return index, Spool(
        count=int(spool_data.get("count", "0").split()[0]),
        oldest=_split_parse_date(spool_data.get("oldest", "")),
        youngest=_split_parse_date(spool_data.get("youngest", "")),
    )


def parse_mknotifyd(  # pylint: disable=too-many-branches
    string_table: StringTable,
) -> MkNotifySection:
    timestamp, data = float(string_table[0][0]), string_table[1:]

    sites: dict[str, Site] = {}

    index = 0
    while index < len(data):
        line = data[index][0]

        if line.startswith("["):
            site_name = line[1:-1]
            spools: dict[str, Spool] = {}
            connections: dict[str, Connection] = {}
            index, version, updated = _parse_site_data(index, data)

            site_entry = Site(
                spools=spools,
                connections=connections,
                version=version,
                updated=updated,
            )
            sites[site_name] = site_entry
        elif ":" in line:
            varname, value = _get_varname_value(line)

            if varname == "Site":
                connected_site = value.split(" (")[0]
            elif varname == "Spool":
                index, site_entry.spools[value] = _get_spool(index, data)
            elif varname == "Connection":
                index, connection = _get_connection(index, data)
                # for "mknotifyd.connection_v2"
                site_entry.connections[connected_site] = connection
                # keep the "mknotifyd.connection" services working
                site_entry.connections[value] = connection

        index += 1

    # Fixup names of the connections. For incoming connections the remote
    # port is irrelevant. It changes randomly. But there might anyway be
    # more than one connection from the same remote host, so we are forced
    # to create artificial numbers if that is the case
    for stats in sites.values():
        remote_addresses: dict = {}
        for connection_name, connection in list(stats.connections.items()):
            if connection.type_ == "incoming":
                remote_address_site = connection_name.split(":")[0]
                remote_addresses.setdefault(remote_address_site, []).append(connection)
                del stats.connections[connection_name]

        for address, connections_group in remote_addresses.items():
            if len(connections_group) == 1:
                stats.connections[address] = connections_group[0]
            else:
                for nr, connection in enumerate(connections_group):
                    stats.connections[address + "/" + str(nr + 1)] = connection

    return MkNotifySection(timestamp=timestamp, sites=sites)


agent_section_mknotifyd = AgentSection(name="mknotifyd", parse_function=parse_mknotifyd)


#   .--Spooler Status------------------------------------------------------.
#   | ____                    _             ____  _        _               |
#   |/ ___| _ __   ___   ___ | | ___ _ __  / ___|| |_ __ _| |_ _   _ ___   |
#   |\___ \| '_ \ / _ \ / _ \| |/ _ \ '__| \___ \| __/ _` | __| | | / __|  |
#   | ___) | |_) | (_) | (_) | |  __/ |     ___) | || (_| | |_| |_| \__ \  |
#   ||____/| .__/ \___/ \___/|_|\___|_|    |____/ \__\__,_|\__|\__,_|___/  |
#   |      |_|                                                             |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_mknotifyd(section: MkNotifySection) -> DiscoveryResult:
    yield from [Service(item=p) for p in section.sites]


def check_mknotifyd(item: str, section: MkNotifySection) -> CheckResult:
    if (site := section.sites.get(item)) is None:
        return

    # There are dummy-entries created during the parsing. So the
    # dict will never be completely empty. We check for Version
    # because this should be always present in a valid state file.
    if site.version is None or site.updated is None:
        yield Result(
            state=State.CRIT,
            summary="The state file seems to be empty or corrupted. It is very likely that the spooler is not working properly",
        )
        return
    yield Result(state=State.OK, summary=f"Version: {site.version}")

    # Check age of status file. It's updated every 20 seconds
    status_age = section.timestamp - site.updated
    if status_age > 90:
        yield Result(
            state=State.CRIT,
            summary=f"Status last updated {render.timespan(status_age)} ago, spooler seems crashed or busy",
        )
    else:
        yield Result(state=State.OK, summary="Spooler running")
    yield Metric("last_updated", status_age)
    yield Metric("new_files", site.spools["New"].count)

    corrupted_spool = site.spools["Corrupted"]
    if corrupted_spool.count and corrupted_spool.youngest is not None:
        age = section.timestamp - corrupted_spool.youngest

        yield Result(
            state=State.WARN,
            summary=f"{corrupted_spool.count} corrupted files: youngest {render.timespan(age)} ago",
        )
        yield Metric("corrupted_files", corrupted_spool.count)

    # Are there deferred files that are too old?
    deferred_spool = site.spools["Deferred"]
    if deferred_spool.count and deferred_spool.oldest is not None:
        count = deferred_spool.count
        age = section.timestamp - deferred_spool.oldest
        if age > 5:
            state = State.WARN
        elif age > 600:  # TODO
            state = State.CRIT
        else:
            state = State.OK
        yield Result(
            state=state, summary=f"{count} deferred files: oldest {render.timespan(age)} ago"
        )
        yield Metric("deferred_age", age)
        yield Metric("deferred_files", count)


check_plugin_mknotifyd = CheckPlugin(
    name="mknotifyd",
    service_name="OMD %s Notification Spooler",
    discovery_function=discover_mknotifyd,
    check_function=check_mknotifyd,
)

#   .--Connections---------------------------------------------------------.
#   |        ____                            _   _                         |
#   |       / ___|___  _ __  _ __   ___  ___| |_(_) ___  _ __  ___         |
#   |      | |   / _ \| '_ \| '_ \ / _ \/ __| __| |/ _ \| '_ \/ __|        |
#   |      | |__| (_) | | | | | | |  __/ (__| |_| | (_) | | | \__ \        |
#   |       \____\___/|_| |_|_| |_|\___|\___|\__|_|\___/|_| |_|___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_mknotifyd_connection(section: MkNotifySection) -> DiscoveryResult:
    # deprecated, do not discover anything
    return
    yield


_V2_SERVICE_NAMING = "Notification Spooler connection to"


def check_mknotifyd_connection(item: str, section: MkNotifySection) -> CheckResult:

    # "mknotifyd.connection_v2"
    if _V2_SERVICE_NAMING in item:
        site_name, connection_name = item.split(f" {_V2_SERVICE_NAMING} ", 1)
    # "mknotifyd.connection"
    else:
        site_name, connection_name = item.split("-", 1)

    if site_name not in section.sites:
        return

    states = {
        "established": (0, "Alive"),
        "cooldown": (2, "Connection failed or terminated"),
        "initial": (1, "Initialized"),
        "connecting": (2, "Trying to connect"),
    }

    if (connection := section.sites[site_name].connections.get(connection_name)) is not None:

        state, summary = states[connection.state]
        yield Result(state=State(state), summary=summary)

        if connection.status_message is not None:
            yield Result(state=State.OK, summary=connection.status_message)

        if connection.state == "established":
            age = section.timestamp - connection.since
            yield Result(state=State.OK, summary=f"Uptime: {render.timespan(age)}")

            if connection.connect_time is not None:
                yield Result(
                    state=State.OK, summary=f"Connect time: {connection.connect_time:.3f} sec"
                )

        if connection.notifications_sent:
            yield Result(
                state=State.OK, summary=f"{connection.notifications_sent} Notifications sent"
            )
        if connection.notifications_received:
            yield Result(
                state=State.OK,
                summary=f"{connection.notifications_received} Notifications received",
            )


check_plugin_mknotifyd_connection = CheckPlugin(
    name="mknotifyd_connection",
    service_name="OMD %s Notify Connection",
    sections=["mknotifyd"],
    discovery_function=discover_mknotifyd_connection,
    check_function=check_mknotifyd_connection,
)


def discover_mknotifyd_connection_v2(section: MkNotifySection) -> DiscoveryResult:
    for site_name, site in section.sites.items():
        for connection_name in site.connections:
            if "." in connection_name:
                # item of old discovered "mknotifyd.connection"
                continue
            yield Service(item=f"{site_name} Notification Spooler connection to {connection_name}")


check_plugin_mknotifyd_connection_v2 = CheckPlugin(
    name="mknotifyd_connection_v2",
    service_name="OMD %s",
    sections=["mknotifyd"],
    discovery_function=discover_mknotifyd_connection_v2,
    check_function=check_mknotifyd_connection,
)
