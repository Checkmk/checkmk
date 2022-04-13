#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Iterable, Iterator, Mapping, Optional, Sequence

from .agent_based_api.v1 import check_levels, regex, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

# <<<systemd_units>>>
#   UNIT                                   LOAD   ACTIVE SUB    DESCRIPTION
# ● check-mk-enterprise-2018.07.24.service loaded failed failed LSB: OMD sites
# ● systemd-cryptsetup@cryptswap1.service  loaded failed failed Cryptography Setup for cryptswap1
# ● swapfile.swap                          loaded failed failed /swapfile
#
# LOAD   = Reflects whether the unit definition was properly loaded.
# ACTIVE = The high-level unit activation state, i.e. generalization of SUB.
# SUB    = The low-level unit activation state, values depend on unit type.
#
# 3 loaded units listed. Pass --all to see loaded but inactive units, too.
# To show all installed unit files use 'systemctl list-unit-files'.

#   .--Parse function------------------------------------------------------.
#   |  ____                        __                  _   _               |
#   | |  _ \ __ _ _ __ ___  ___   / _|_   _ _ __   ___| |_(_) ___  _ __    |
#   | | |_) / _` | '__/ __|/ _ \ | |_| | | | '_ \ / __| __| |/ _ \| '_ \   |
#   | |  __/ (_| | |  \__ \  __/ |  _| |_| | | | | (__| |_| | (_) | | | |  |
#   | |_|   \__,_|_|  |___/\___| |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|  |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# .service
#             A service unit describes how to manage a service or application on the
#             server. This will include how to start or stop the service, under which
#             circumstances it should be automatically started, and the dependency and
#             ordering information for related software.
# .socket
#             A socket unit file describes a network or IPC socket, or a FIFO buffer
#             that systemd uses for socket-based activation. These always have an
#             associated .service file that will be started when activity is seen on the
#             socket that this unit defines.
# .device
#             A unit that describes a device that has been designated as needing
#             systemd management by udev or the sysfs filesystem. Not all devices will
#             have .device files. Some scenarios where .device units may be necessary are
#             for ordering, mounting, and accessing the devices.
# .mount
#             This unit defines a mountpoint on the system to be managed by systemd.
#             These are named after the mount path, with slashes changed to dashes.
#             Entries within /etc/fstab can have units created automatically.
# .automount
#             An .automount unit configures a mountpoint that will be automatically
#             mounted. These must be named after the mount point they refer to and must
#             have a matching .mount unit to define the specifics of the mount.
# .swap
#             This unit describes swap space on the system. The name of these units
#             must reflect the device or file path of the space.
# .target
#             A target unit is used to provide synchronization points for other units
#             when booting up or changing states. They also can be used to bring the
#             system to a new state. Other units specify their relation to targets to
#             become tied to the target's operations.
# .path
#             This unit defines a path that can be used for path-based activation. By
#             default, a .service unit of the same base name will be started when the
#             path reaches the specified state. This uses inotify to monitor the path for
#             changes.
# .timer
#             A .timer unit defines a timer that will be managed by systemd, similar to
#             a cron job for delayed or scheduled activation. A matching unit will be
#             started when the timer is reached.
# .snapshot
#             A .snapshot unit is created automatically by the systemctl snapshot
#             command. It allows you to reconstruct the current state of the system after
#             making changes. Snapshots do not survive across sessions and are used to
#             roll back temporary states.
# .slice
#             A .slice unit is associated with Linux Control Group nodes, allowing
#             resources to be restricted or assigned to any processes associated with the
#             slice. The name reflects its hierarchical position within the cgroup tree.
#             Units are placed in certain slices by default depending on their type.
# .scope
#             Scope units are created automatically by systemd from information
#             received from its bus interfaces. These are used to manage sets of system
#             processes that are created externally.


_SYSTEMD_UNIT_FILE_STATES = [
    "enabled",
    "enabled-runtime",
    "linked",
    "linked-runtime",
    "masked",
    "masked-runtime",
    "static",
    "indirect",
    "disabled",
    "generated",
    "transient",
    "bad",
]


@dataclass(frozen=True)
class UnitEntry:
    name: str
    loaded_status: str
    active_status: str
    current_state: str
    description: str
    enabled_status: str
    time_since_change: Optional[timedelta] = None


Section = Mapping[str, UnitEntry]


def _parse_list_unit_files(source: Iterator[Sequence[str]]) -> Mapping[str, str]:
    return {
        line[0]: line[1]
        for line in source
        if len(line) >= 2 and line[1] in _SYSTEMD_UNIT_FILE_STATES
    }


# systemd implementation for generating the time string we want to parse
# https://github.com/systemd/systemd/blob/c87c30780624df257ed96909a2286b2b933f8c44/src/basic/time-util.c#L417
#
# number of seconds in a year and month according to systemd
# https://github.com/systemd/systemd/blob/2afb2f4a9d6a497dfbe1983fbe1bac297a8dc52b/src/basic/time-util.h#L60
def _parse_time_str(string: str) -> timedelta:
    kwargs: dict[str, int] = defaultdict(int)
    SEC_PER_MONTH = 2629800
    SEC_PER_YEAR = 31557600
    kwarg_parsers = [
        ("microseconds", regex("([0-9]?[0-9]?[0-9])us"), 1),
        ("milliseconds", regex("([0-9]?[0-9]?[0-9])ms"), 1),
        ("seconds", regex("([0-6]?[0-9])s"), 1),
        ("minutes", regex("([0-6]?[0-9])min"), 1),
        ("hours", regex("([0-2]?[0-9])h"), 1),
        ("days", regex("([0-2]?[0-9]) days?"), 1),
        ("weeks", regex("([0-4]) weeks?"), 1),
        ("seconds", regex("([0-9]?[0-9]?[0-9]) months?"), SEC_PER_MONTH),
        ("seconds", regex("([0-9]?[0-9]?[0-9]) years?"), SEC_PER_YEAR),
    ]
    for time_unit, rgx, scale in kwarg_parsers:
        if match := rgx.search(string):
            kwargs[time_unit] += scale * int(match.groups()[0])

    return timedelta(**kwargs)


@dataclass(frozen=True)
class UnitStatus:
    name: str
    status: str
    time_since_change: Optional[timedelta]

    @classmethod
    def from_entry(cls, entry: Sequence[Sequence[str]]) -> "UnitStatus":
        name = entry[0][1].split(".", 1)[0]
        timestr = " ".join(entry[2]).split(";", 1)[-1]
        if "ago" in timestr:
            time_since_change = _parse_time_str(timestr.replace("ago", "").strip())
        else:
            time_since_change = None
        return cls(name=name, status=entry[2][1], time_since_change=time_since_change)


def _parse_all(
    source: Iterable[list[str]],
    enabled_status: Mapping[str, str],
    status_details: Mapping[str, UnitStatus],
) -> Optional[Section]:
    parsed: dict[str, UnitEntry] = {}
    for row in source:
        if row[0] in {"●", "*"}:
            row = row[1:]
        if row[0].endswith(".service"):
            name = row[0].replace(".service", "")
            temp = name[: name.find("@") + 1] if "@" in name else name
            enabled = enabled_status.get(f"{temp}.service", "unknown")
            remains = " ".join(row[1:])
            loaded_status, active_status, current_state, descr = remains.split(" ", 3)
            time_since_change = (
                status_details[name].time_since_change if name in status_details else None
            )
            unit = UnitEntry(
                name,
                loaded_status,
                active_status,
                current_state,
                descr,
                enabled,
                time_since_change=time_since_change,
            )
            parsed[unit.name] = unit
    if parsed == {}:
        return None
    return parsed


def _is_service_entry(entry: Sequence[Sequence[str]]) -> bool:
    unit = entry[0][1]
    return unit.endswith(".service")


def _parse_status(source: Iterator[Sequence[str]]) -> Mapping[str, UnitStatus]:
    unit_status = {}
    entry: list[Sequence[str]] = []
    for line in source:
        # see sources for all possible glyphs to start a service status section
        # https://github.com/systemd/systemd/blob/7d4054464318d15ecd35c93fb477011aec63391e/src/basic/unit-def.c#L307
        # translatons for non utf8 terminals
        # https://github.com/systemd/systemd/blob/7d4054464318d15ecd35c93fb477011aec63391e/src/basic/glyph-util.c#L38
        if line[0] in {"●", "○", "↻", "×", "x", "*"}:
            if entry != [] and _is_service_entry(entry):
                status = UnitStatus.from_entry(entry)
                unit_status[status.name] = status
            entry = [
                line,
            ]
            continue
        if line[0].startswith("[all]"):
            break
        entry.append(line)
    if len(entry) > 1:
        status = UnitStatus.from_entry(entry)
        unit_status[status.name] = status

    return unit_status


def parse(string_table: StringTable) -> Optional[Section]:
    if not string_table:
        return None
    # This is a hack to know about possible markers that start a new section. Just looking for a "[" is
    # not enough as that can be contained in the systemd output. We also cannot change the section markers
    # as we have to consume agent output from previous versions. A better way would be to have a unique
    # section end marker that does not appear in any systemd output.
    all_sections = {"[list-unit-files]", "[status]", "[all]"}
    sections = defaultdict(list)
    section = None
    for line in string_table:
        if line[0] in all_sections:
            section = line[0][1:-1]
        else:
            sections[section].append(line)

    enabled_status_collection = _parse_list_unit_files(iter(sections["list-unit-files"]))
    status_details = _parse_status(iter(sections["status"]))
    return _parse_all(iter(sections["all"]), enabled_status_collection, status_details)


register.agent_section(name="systemd_units", parse_function=parse)

#   .--services------------------------------------------------------------.
#   |                                     _                                |
#   |                 ___  ___ _ ____   _(_) ___ ___  ___                  |
#   |                / __|/ _ \ '__\ \ / / |/ __/ _ \/ __|                 |
#   |                \__ \  __/ |   \ V /| | (_|  __/\__ \                 |
#   |                |___/\___|_|    \_/ |_|\___\___||___/                 |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discovery_systemd_units_services(
    params: Sequence[Mapping[str, Any]], section: Section
) -> DiscoveryResult:
    # Filter out volatile systemd service units created by the Checkmk agent which appear and
    # disappear frequently. No matter what the user configures, we do not want to discover them.
    filtered_services = [
        service
        for service in section.values()
        if not regex("^check-mk-agent@.+").match(service.name)
    ]

    def regex_match(what: Sequence[str], name: str) -> bool:
        if not what:
            return True
        for entry in what:
            if entry.startswith("~"):
                if regex(entry[1:]).match(name):
                    return True
                continue
            if entry == name:
                return True
        return False

    def state_match(rule_states: Sequence[str], state: str) -> bool:
        if not rule_states:
            return True
        return any(s in (None, state) for s in rule_states)

    # defaults are always last and empty to apeace the new api
    for service in filtered_services:
        for settings in params:
            descriptions = settings.get("descriptions", [])
            names = settings.get("names", [])
            states = settings.get("states", [])
            if (
                regex_match(descriptions, service.description)
                and regex_match(names, service.name)
                and state_match(states, service.active_status)
            ):
                yield Service(item=service.name)
                continue


def check_systemd_units_services(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    # A service found in the discovery phase can vanish in subsequent runs. I.e. the systemd service was deleted during an update
    if item not in section:
        yield Result(state=State(params["else"]), summary="Service not found")
        return
    service = section[item]
    # TODO: this defaults unkown states to CRIT with the default params
    state = params["states"].get(service.active_status, params["states_default"])
    yield Result(state=State(state), summary=f"Status: {service.active_status}")
    yield Result(state=State.OK, summary=service.description)


register.check_plugin(
    name="systemd_units_services",
    sections=["systemd_units"],
    service_name="Systemd Service %s",
    check_ruleset_name="systemd_services",
    discovery_function=discovery_systemd_units_services,
    discovery_default_parameters={"names": ["(never discover)^"]},
    discovery_ruleset_name="discovery_systemd_units_services_rules",
    discovery_ruleset_type=register.RuleSetType.ALL,
    check_function=check_systemd_units_services,
    check_default_parameters={
        "states": {
            "active": 0,
            "inactive": 0,
            "failed": 2,
        },
        "states_default": 2,
        "else": 2,  # missleading name, used if service vanishes
    },
)


def discovery_systemd_units_services_summary(section: Section) -> DiscoveryResult:
    yield Service()


def _services_split(
    services: Iterable[UnitEntry], blacklist: Sequence[str]
) -> Mapping[str, list[UnitEntry]]:
    services_organised: dict[str, list[UnitEntry]] = {
        "included": [],
        "excluded": [],
        "disabled": [],
        "activating": [],
        "deactivating": [],
        "reloading": [],
        "static": [],
    }
    compiled_patterns = [regex(p) for p in blacklist]
    for service in services:
        if any(expr.match(service.name) for expr in compiled_patterns):
            services_organised["excluded"].append(service)
            continue
        if service.active_status in ("activating", "deactivating"):
            services_organised[service.active_status].append(service)
        elif service.enabled_status in ("reloading", "disabled", "static", "indirect"):
            service_type = (
                "disabled" if service.enabled_status == "indirect" else service.enabled_status
            )
            services_organised[service_type].append(service)
        else:
            services_organised["included"].append(service)
    return services_organised


def _check_temporary_state(
    services: Iterable[UnitEntry], params: Mapping[str, Any], service_state: str
) -> CheckResult:
    levels = params[f"{service_state}_levels"]
    for service in services:
        elapsed_time = service.time_since_change
        if elapsed_time is None:
            continue
        yield from check_levels(
            elapsed_time.total_seconds(),
            levels_upper=levels,
            render_func=render.timespan,
            label=f"Service '{service.name}' {service_state} for",
            notice_only=True,
        )


def _check_non_ok_services(
    systemd_services: Iterable[UnitEntry], params: Mapping[str, Any], output_string: str
) -> Iterable[Result]:
    servicenames_by_status: dict[Any, Any] = {}
    for service in systemd_services:
        servicenames_by_status.setdefault(service.active_status, []).append(service.name)

    for status, service_names in sorted(servicenames_by_status.items()):
        # TODO: really default to CRIT if we do not know a state after a systemd updates?
        state = State(params["states"].get(status, params["states_default"]))
        if state == State.OK:
            continue

        count = len(service_names)
        services_text = ", ".join(sorted(service_names))
        info = output_string.format(
            count=count,
            is_plural="" if count == 1 else "s",
            status=status,
            service_text=services_text,
        )

        yield Result(state=State(state), summary=info)


def check_systemd_units_services_summary(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    services = section.values()
    blacklist = params["ignored"]
    yield Result(state=State.OK, summary=f"Total: {len(services):d}")
    services_organised = _services_split(services, blacklist)
    yield Result(state=State.OK, summary=f"Disabled: {len(services_organised['disabled']):d}")
    # some of the failed ones might be ignored, so this is OK:
    yield Result(
        state=State.OK, summary=f"Failed: {sum(s.active_status == 'failed' for s in services):d}"
    )
    included_template = "{count:d} service{is_plural} {status} ({service_text})"
    yield from _check_non_ok_services(services_organised["included"], params, included_template)

    static_template = "{count:d} static service{is_plural} {status} ({service_text})"
    yield from _check_non_ok_services(services_organised["static"], params, static_template)

    for temporary_type in ("activating", "reloading", "deactivating"):
        yield from _check_temporary_state(
            services_organised[temporary_type], params, temporary_type
        )
    if services_organised["excluded"]:
        yield Result(state=State.OK, notice=f"Ignored: {len(services_organised['excluded']):d}")


register.check_plugin(
    name="systemd_units_services_summary",
    sections=["systemd_units"],
    discovery_function=discovery_systemd_units_services_summary,
    check_function=check_systemd_units_services_summary,
    check_ruleset_name="systemd_services_summary",
    service_name="Systemd Service Services",
    check_default_parameters={
        "states": {
            "active": 0,
            "inactive": 0,
            "failed": 2,
        },
        "states_default": 2,
        "activating_levels": (30, 60),
        "deactivating_levels": (30, 60),
        "reloading_levels": (30, 60),
        "ignored": [],
    },
)
