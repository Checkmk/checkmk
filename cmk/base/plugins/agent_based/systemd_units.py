#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from collections import defaultdict
from typing import Any, Iterable, Mapping, NamedTuple, Sequence

from .agent_based_api.v1 import (
    check_levels,
    get_value_store,
    regex,
    register,
    render,
    Result,
    Service,
    State,
)
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

_SYSTEMD_UNITS = [
    ".service ",
    ".socket ",
    ".device ",
    ".mount ",
    ".automount ",
    ".swap ",
    ".target ",
    ".path ",
    ".timer ",
    ".snapshot ",
    ".slice ",
    ".scope ",
]

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


class UnitEntry(NamedTuple):
    name: str
    unit_type: str
    loaded_status: str
    active_status: str
    current_state: str
    description: str
    enabled_status: str


Section = Mapping[str, Mapping[str, UnitEntry]]


def parse(string_table: StringTable) -> Section:
    if not string_table:
        return {}

    iter_string_table = iter(string_table)
    enabled_status_collection = {}

    line = next(iter_string_table)

    if line[0] == "[list-unit-files]":
        for line in iter_string_table:
            if line[0].startswith("["):
                break
            if len(line) >= 2 and line[1] in _SYSTEMD_UNIT_FILE_STATES:
                enabled_status_collection[line[0]] = line[1]

    parsed: dict[str, dict[str, UnitEntry]] = defaultdict(dict)
    if line[0] == "[all]":
        try:
            line = next(iter_string_table)

        # no services listed
        except StopIteration:
            return parsed

        for row in iter_string_table:
            if row[0] in {"●", "*"}:
                row.pop(0)
            joinedline = " ".join(row)
            for unit_marker in _SYSTEMD_UNITS:
                utype = unit_marker.strip(" ")
                if row[0].endswith(utype):
                    unit_type = unit_marker.strip(". ")
                    name, remains = joinedline.split(unit_marker, 1)
                    if "@" in name:
                        pos = name.find("@")
                        temp = name[: pos + 1]
                    else:
                        temp = name
                    enabled_status = enabled_status_collection.get(
                        "%s.%s" % (temp, unit_type),
                        "unknown",
                    )
                    loaded_status, active_status, current_state, descr = remains.split(" ", 3)
                    unit = UnitEntry(
                        name,
                        unit_type,
                        loaded_status,
                        active_status,
                        current_state,
                        descr,
                        enabled_status,
                    )
                    parsed[unit.unit_type][unit.name] = unit
                    break
    return parsed


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
        for service in section.get("service", {}).values()
        if not regex("^check-mk-agent@.+").match(service.name)
    ]

    def regex_match(what, name):
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

    def state_match(rule_states, state):
        if not rule_states:
            return True
        return any(s in (None, state) for s in rule_states)

    for settings in params:
        descriptions = settings.get("descriptions", [])
        names = settings.get("names", [])
        states = settings.get("states", [])
        for service in filtered_services:
            if (
                regex_match(descriptions, service.description)
                and regex_match(names, service.name)
                and state_match(states, service.active_status)
            ):
                yield Service(item=service.name)


def check_systemd_units_services(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    services = section.get("service", {})
    service = services.get(item, None)
    if service is None:
        yield Result(state=State(params["else"]), summary="Service not found")
        return

    state = params["states"].get(service.active_status, params["states_default"])
    yield Result(state=State(state), summary=f"Status: {service.active_status}")
    yield Result(state=State.OK, summary=service.description)


register.check_plugin(
    name="systemd_units_services",
    sections=["systemd_units"],
    service_name="Systemd Service %s",
    check_ruleset_name="systemd_services",
    discovery_function=discovery_systemd_units_services,
    discovery_default_parameters={},
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


def _services_split(services, blacklist):
    services_organised: dict[str, list] = {
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


def _check_temporary_state(services, params, service_state) -> CheckResult:
    value_store = get_value_store()
    previous_state = value_store.get(service_state, {})
    now = int(time.time())
    current_state = {}
    levels = params.get("%s_levels" % service_state)
    for service in services:
        state_since = previous_state.get(service.name, now)
        current_state[service.name] = state_since
        elapsed_time = now - state_since
        yield from check_levels(
            elapsed_time,
            levels_upper=levels,
            render_func=render.timespan,
            label="Service '%s' %s for" % (service.name, service_state),
            notice_only=True,
        )

    value_store[service_state] = current_state


def _check_non_ok_services(systemd_services, params, output_string) -> Iterable[Result]:
    servicenames_by_status: dict[Any, Any] = {}
    for service in systemd_services:
        servicenames_by_status.setdefault(service.active_status, []).append(service.name)

    for status, service_names in sorted(servicenames_by_status.items()):
        state = State(params["states"].get(status, params["states_default"]))
        if state == State.OK:
            continue

        count = len(service_names)
        services_text = ", ".join(sorted(service_names))
        info = output_string % (count, "" if count == 1 else "s", status, services_text)

        yield Result(state=State(state), summary=info)


def check_systemd_units_services_summary(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    services = section.get("service", {}).values()
    blacklist = params.get("ignored", [])
    yield Result(state=State.OK, summary="Total: %d" % len(services))
    services_organised = _services_split(services, blacklist)
    yield Result(state=State.OK, summary="Disabled: %d" % len(services_organised["disabled"]))
    # some of the failed ones might be ignored, so this is OK:
    yield Result(
        state=State.OK, summary="Failed: %d" % sum(s.active_status == "failed" for s in services)
    )
    included_template = "%d service%s %s (%s)"
    yield from _check_non_ok_services(services_organised["included"], params, included_template)

    static_template = "%d static service%s %s (%s)"
    yield from _check_non_ok_services(services_organised["static"], params, static_template)

    for temporary_type in ("activating", "reloading", "deactivating"):
        yield from _check_temporary_state(
            services_organised[temporary_type], params, temporary_type
        )
    if services_organised["excluded"]:
        yield Result(state=State.OK, notice="Ignored: %d" % len(services_organised["excluded"]))


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
    },
)
