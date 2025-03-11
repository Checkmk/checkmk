#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Any, NamedTuple

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
    # TODO: alias is missing. is this by accident?
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

# see sources for all possible glyphs to start a service status section
# https://github.com/systemd/systemd/blob/7d4054464318d15ecd35c93fb477011aec63391e/src/basic/unit-def.c#L307
# translatons for non utf8 terminals
# https://github.com/systemd/systemd/blob/7d4054464318d15ecd35c93fb477011aec63391e/src/basic/glyph-util.c#L38
_STATUS_SYMBOLS = {"●", "○", "↻", "×", "x", "*"}


# See: https://www.freedesktop.org/software/systemd/man/systemd.unit.html
class UnitTypes(Enum):
    # When adding new systemd units, keep in mind to extend the gathering of the data via
    # the linux agent. Currently, we're only querying service and socket.
    service = "service"
    socket = "socket"

    @property
    def suffix(self):
        return f".{self.value}"

    @property
    def singular(self):
        return f"{self.value.capitalize()}"

    @property
    def plural(self):
        return f"{self.value.capitalize()}s"


@dataclass(frozen=True)
class UnitStatus:
    name: str
    status: str
    enabled_status: str | None
    time_since_change: timedelta | None

    @classmethod
    def from_entry(cls, entry: Sequence[Sequence[str]]) -> "UnitStatus":
        name = entry[0][1].split(".", 1)[0]
        enabled_status = entry[1][3].rstrip(";)") if len(entry[1]) >= 4 else None

        time_line = next((line for line in entry if line[0].lstrip().startswith("Active:")), [])
        timestr = " ".join(time_line).split(";", 1)[-1]
        if "ago" in timestr:
            time_since_change = _parse_time_str(timestr.replace("ago", "").strip())
        else:
            time_since_change = None
        return cls(
            name=name,
            status=entry[2][1],
            time_since_change=time_since_change,
            enabled_status=enabled_status,
        )


@dataclass(frozen=True)
class UnitEntry:
    name: str
    loaded_status: str  # LOAD   = Reflects whether the unit definition was properly loaded.
    #                     for example: loaded, not-found, bad-setting, error, masked
    active_status: str  # ACTIVE = The high-level unit activation state, i.e. generalization of SUB.
    #                     for example: active, reloading, inactive, failed, activating, deactivating
    current_state: str  # SUB    = The low-level unit activation state, values depend on unit type.
    # The list of possible LOAD, ACTIVE, and SUB states is not constant and new systemd releases may
    # both add and remove values. See systemctl --state=help
    description: str
    enabled_status: (
        str | None
    )  # see "Available unit file states:" in `systemctl --state=help` or _SYSTEMD_UNIT_FILE_STATES
    time_since_change: timedelta | None = None

    @classmethod
    def _parse_name_and_unit_type(cls, raw: str) -> None | tuple[str, UnitTypes]:
        """
        >>> UnitEntry._parse_name_and_unit_type("foobar.service")
        ('foobar', <UnitTypes.service: 'service'>)
        >>> UnitEntry._parse_name_and_unit_type("another.bar.service")
        ('another.bar', <UnitTypes.service: 'service'>)
        >>> UnitEntry._parse_name_and_unit_type("another.bar.not_a_know_unit") is None
        True
        """
        for unit in UnitTypes:
            if raw.endswith(unit.suffix):
                return raw.replace(unit.suffix, ""), unit
        return None

    @classmethod
    def try_parse(
        cls,
        row: Sequence[str],
        enabled_status: Mapping[str, str],
        status_details: Mapping[str, UnitStatus],
    ) -> tuple[UnitTypes, "UnitEntry"] | None:
        if not (name_unit := cls._parse_name_and_unit_type(row[0])):
            return None
        name, unit_type = name_unit
        temp = name[: name.find("@") + 1] if "@" in name else name
        # Prefer enabled state from the status section over the list-unit-files, it is the actual instantiation of a service
        # The status section is generated by the agent since a6a979ce and may not be present
        enabled = (
            status_details[name].enabled_status
            if name in status_details
            else enabled_status.get(f"{temp}{unit_type.suffix}")
        )
        remains = " ".join(row[1:])
        loaded_status, active_status, current_state, descr = remains.split(" ", 3)
        time_since_change = (
            status_details[name].time_since_change if name in status_details else None
        )
        return unit_type, UnitEntry(
            name=name,
            loaded_status=loaded_status,
            active_status=active_status,
            current_state=current_state,
            description=descr,
            enabled_status=enabled,
            time_since_change=time_since_change,
        )


Units = Mapping[str, UnitEntry]


class Section(NamedTuple):
    services: Units
    sockets: Units


def _parse_list_unit_files(source: Iterator[Sequence[str]]) -> Mapping[str, str]:
    return {
        line[0]: line[1]
        for line in source
        if len(line) >= 2 and line[1] in _SYSTEMD_UNIT_FILE_STATES
    }


KWARG_PARSERS = [
    ("microseconds", regex("([0-9]?[0-9]?[0-9])us"), 1),
    ("milliseconds", regex("([0-9]?[0-9]?[0-9])ms"), 1),
    ("seconds", regex("([0-6]?[0-9])s"), 1),
    ("minutes", regex("([0-6]?[0-9])min"), 1),
    ("hours", regex("([0-2]?[0-9])h"), 1),
    ("days", regex("([0-2]?[0-9]) days?"), 1),
    ("weeks", regex("([0-4]) weeks?"), 1),
    ("seconds", regex("([0-9]?[0-9]?[0-9]) months?"), int(60 * 60 * 24 * 30.4375)),
    ("seconds", regex("([0-9]?[0-9]?[0-9]) years?"), int(60 * 60 * 24 * 365.25)),
]


# systemd implementation for generating the time string we want to parse
# https://github.com/systemd/systemd/blob/c87c30780624df257ed96909a2286b2b933f8c44/src/basic/time-util.c#L417
#
# number of seconds in a year and month according to systemd
# https://github.com/systemd/systemd/blob/2afb2f4a9d6a497dfbe1983fbe1bac297a8dc52b/src/basic/time-util.h#L60
def _parse_time_str(string: str) -> timedelta:
    kwargs: dict[str, int] = defaultdict(int)

    for time_unit, rgx, scale in KWARG_PARSERS:
        if match := rgx.search(string):
            kwargs[time_unit] += scale * int(match.groups()[0])

    return timedelta(**kwargs)


def _parse_all(
    source: Iterable[list[str]],
    enabled_status: Mapping[str, str],
    status_details: Mapping[str, UnitStatus],
) -> Section:
    services: dict[str, UnitEntry] = {}
    sockets: dict[str, UnitEntry] = {}
    for row in source:
        if row[0] in _STATUS_SYMBOLS:
            row = row[1:]
        if result := UnitEntry.try_parse(row, enabled_status, status_details):
            unit_type, unit = result
            if unit_type is UnitTypes.service:
                services[unit.name] = unit
            if unit_type is UnitTypes.socket:
                sockets[unit.name] = unit
    return Section(services=services, sockets=sockets)


def _is_service_entry(entry: Sequence[Sequence[str]]) -> bool:
    try:
        unit = entry[0][1]
    except IndexError:
        return False
    return unit.endswith(".service")


SERVICE_REGEX = re.compile(
    r".+\.(service|socket|device|mount|automount|swap|target|path|timer|slice|scope)$"
)
# hopefully all possible unit types as described in https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html#Description


def _is_new_entry(line: Sequence[str], entry: list[Sequence[str]]) -> bool:
    # First check if we're not looking at a "Triggers" section.
    # It looks like the beginning of a new status entry, e.g.:
    # "Triggers: ● check-mk-agent@3148-1849349-997.service",
    # "● check-mk-agent@3149-1849349-997.service",
    for elem in reversed(entry):
        if elem[0].startswith("Triggers:"):
            return False
        if elem[0] not in _STATUS_SYMBOLS:
            break
    return (
        (line[0] in _STATUS_SYMBOLS)
        and (len(line) >= 2)
        and (bool(SERVICE_REGEX.match(str(line[1]))))
    )


def _parse_status(source: Iterator[Sequence[str]]) -> Mapping[str, UnitStatus]:
    unit_status = {}
    entry: list[Sequence[str]] = []
    for line in source:
        if _is_new_entry(line, entry):
            if entry and _is_service_entry(entry):
                status = UnitStatus.from_entry(entry)
                unit_status[status.name] = status
            entry = [
                line,
            ]
            continue
        entry.append(line)
    if len(entry) > 1 and _is_service_entry(entry):
        status = UnitStatus.from_entry(entry)
        unit_status[status.name] = status

    return unit_status


def parse(string_table: StringTable) -> Section | None:
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

#   .--units---------------------------------------------------------------.
#   |                                    _ _                               |
#   |                        _   _ _ __ (_) |_ ___                         |
#   |                       | | | | '_ \| | __/ __|                        |
#   |                       | |_| | | | | | |_\__ \                        |
#   |                        \__,_|_| |_|_|\__|___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discovery_systemd_units_services(
    params: Sequence[Mapping[str, Any]], section: Section
) -> DiscoveryResult:
    # Filter out volatile systemd service created by the Checkmk agent which appear and
    # disappear frequently. No matter what the user configures, we do not want to discover them.
    filtered_services = [
        unit_entry
        for unit_entry in section.services.values()
        if not regex("^check-mk-agent@.+").match(unit_entry.name)
    ]
    yield from discovery_systemd_units(params, filtered_services)


def discovery_systemd_units_sockets(
    params: Sequence[Mapping[str, Any]], section: Section
) -> DiscoveryResult:
    yield from discovery_systemd_units(params, list(section.sockets.values()))


def discovery_systemd_units(
    params: Sequence[Mapping[str, Any]], units: Sequence[UnitEntry]
) -> DiscoveryResult:
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
    for unit in units:
        for settings in params:
            descriptions = settings.get("descriptions", [])
            names = settings.get("names", [])
            states = settings.get("states", [])
            if (
                regex_match(descriptions, unit.description)
                and regex_match(names, unit.name)
                and state_match(states, unit.active_status)
            ):
                yield Service(item=unit.name)
                continue


def check_systemd_services(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_systemd_units(item, params, section.services)


def check_systemd_sockets(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_systemd_units(item, params, section.sockets)


def check_systemd_units(item: str, params: Mapping[str, Any], units: Units) -> CheckResult:
    # A service found in the discovery phase can vanish in subsequent runs. I.e. the systemd service was deleted during an update
    if item not in units:
        yield Result(
            state=State(params["else"]),
            summary="Unit not found",
            details="Only units currently in memory are found. These can be shown with `systemctl --all --type service --type socket`.",
        )
        return
    unit = units[item]
    # TODO: this defaults unknown states to CRIT with the default params
    state = params["states"].get(unit.active_status, params["states_default"])
    yield Result(state=State(state), summary=f"Status: {unit.active_status}")
    yield Result(state=State.OK, summary=unit.description)


CHECK_DEFAULT_PARAMETERS = {
    "states": {
        "active": 0,
        "inactive": 0,
        "failed": 2,
    },
    "states_default": 2,
    "else": 2,  # misleading name, used if service vanishes
}

DISCOVERY_DEFAULT_PARAMETERS = {"names": ["(never discover)^"]}

register.check_plugin(
    name="systemd_units_services",
    sections=["systemd_units"],
    service_name="Systemd Service %s",
    check_ruleset_name="systemd_units_services",
    discovery_function=discovery_systemd_units_services,
    discovery_default_parameters=DISCOVERY_DEFAULT_PARAMETERS,
    discovery_ruleset_name="discovery_systemd_units_services",
    discovery_ruleset_type=register.RuleSetType.ALL,
    check_function=check_systemd_services,
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
)
register.check_plugin(
    name="systemd_units_sockets",
    sections=["systemd_units"],
    service_name="Systemd Socket %s",
    check_ruleset_name="systemd_units_sockets",
    discovery_function=discovery_systemd_units_sockets,
    discovery_default_parameters=DISCOVERY_DEFAULT_PARAMETERS,
    discovery_ruleset_name="discovery_systemd_units_sockets",
    discovery_ruleset_type=register.RuleSetType.ALL,
    check_function=check_systemd_sockets,
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
)


def discovery_systemd_units_services_summary(section: Section) -> DiscoveryResult:
    yield Service()


def discovery_systemd_units_sockets_summary(section: Section) -> DiscoveryResult:
    yield Service()


def _services_split(
    services: Iterable[UnitEntry], blacklist: Sequence[str]
) -> Mapping[str, list[UnitEntry]]:
    services_organised: dict[str, list[UnitEntry]] = {
        # early exit:
        "excluded": [],  # based on configured regex
        # based on active_status:
        "activating": [],
        "deactivating": [],
        "reloading": [],
        # based on enabled_status:
        "disabled": [],  # includes also indirect
        "static": [],
        # fallback
        "included": [],  # all others
    }
    compiled_patterns = [regex(p) for p in blacklist]
    for service in services:
        if any(expr.match(service.name) for expr in compiled_patterns) or service.name in blacklist:
            services_organised["excluded"].append(service)
            continue
        if service.active_status in ("reloading", "activating", "deactivating"):
            services_organised[service.active_status].append(service)
        elif service.enabled_status in ("disabled", "static", "indirect"):
            service_type = (
                "disabled" if service.enabled_status == "indirect" else service.enabled_status
            )
            services_organised[service_type].append(service)
        else:
            services_organised["included"].append(service)
    return services_organised


def _check_temporary_state(
    services: Iterable[UnitEntry],
    params: Mapping[str, Any],
    service_state: str,
    unit_type: UnitTypes,
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
            label=f"{unit_type.singular} '{service.name}' {service_state} for",
            notice_only=True,
        )


def _check_non_ok_services(
    systemd_services: Iterable[UnitEntry],
    params: Mapping[str, Any],
    output_string: str,
    unit_type: UnitTypes,
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
            status=status,
            service_text=services_text,
            unit_type=unit_type.singular.casefold() if count == 1 else unit_type.plural.casefold(),
        )

        yield Result(state=State(state), summary=info)


def check_systemd_units_services_summary(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    yield from check_systemd_units_summary(
        params, list(section.services.values()), unit_type=UnitTypes.service
    )


def check_systemd_units_sockets_summary(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_systemd_units_summary(
        params, list(section.sockets.values()), unit_type=UnitTypes.socket
    )


def check_systemd_units_summary(
    params: Mapping[str, Any], units: Sequence[UnitEntry], unit_type: UnitTypes
) -> CheckResult:
    blacklist = params["ignored"]
    yield Result(state=State.OK, summary=f"Total: {len(units):d}")
    services_organised = _services_split(units, blacklist)
    yield Result(state=State.OK, summary=f"Disabled: {len(services_organised['disabled']):d}")

    yield Result(
        state=State(params["states"].get("failed", params["states_default"]))
        if sum(
            s.active_status == "failed"
            for s in units
            if s not in services_organised["excluded"] and s not in services_organised["disabled"]
        )
        else State.OK,
        summary=f"Failed: {sum(s.active_status == 'failed' for s in units)}",
    )

    included_template = "{count:d} {unit_type} {status} ({service_text})"
    yield from _check_non_ok_services(
        services_organised["included"], params, included_template, unit_type
    )

    static_template = "{count:d} static {unit_type} {status} ({service_text})"
    yield from _check_non_ok_services(
        services_organised["static"], params, static_template, unit_type
    )

    for temporary_type in ("activating", "reloading", "deactivating"):
        yield from _check_temporary_state(
            services_organised[temporary_type],
            params,
            temporary_type,
            UnitTypes.service,
        )
    if services_organised["excluded"]:
        yield Result(state=State.OK, notice=f"Ignored: {len(services_organised['excluded']):d}")


CHECK_DEFAULT_PARAMETERS_SUMMARY = {
    "states": {
        "active": 0,
        "inactive": 0,
        "failed": 2,
    },
    "states_default": 2,
    "activating_levels": None,
    "deactivating_levels": (30, 60),
    "reloading_levels": (30, 60),
    "ignored": [],
}

register.check_plugin(
    name="systemd_units_services_summary",
    sections=["systemd_units"],
    discovery_function=discovery_systemd_units_services_summary,
    check_function=check_systemd_units_services_summary,
    check_ruleset_name="systemd_services_summary",
    service_name="Systemd Service Summary",
    check_default_parameters=CHECK_DEFAULT_PARAMETERS_SUMMARY,
)

register.check_plugin(
    name="systemd_units_sockets_summary",
    sections=["systemd_units"],
    discovery_function=discovery_systemd_units_sockets_summary,
    check_function=check_systemd_units_sockets_summary,
    check_ruleset_name="systemd_sockets_summary",
    service_name="Systemd Socket Summary",
    check_default_parameters=CHECK_DEFAULT_PARAMETERS_SUMMARY,
)
