#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Collection, Mapping, Sequence
from typing import Any, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    RuleSetType,
    Service,
    State,
    StringTable,
)


class SolarisService(TypedDict):
    state: str
    stime: str
    type: str
    category: str
    name: str
    instance: str | None


Section = Mapping[str, SolarisService]

DISCOVER_NOTHING = {"descriptions": ["~$^"]}


# OLD
# <<<solaris_services>>>
# STATE    STIME    FMRI
# $STATE   $STIME   $TYPE:${/CATEGORY/PATH/}$NAME:$INSTANCE


def _get_parts_of_descr(descr: str) -> tuple[str, str, str, str | None]:
    svc_attrs = descr.split(":")
    if len(svc_attrs) == 3:
        svc_instance = svc_attrs[-1]
    else:
        svc_instance = None
    svc_category, svc_name = svc_attrs[1].rsplit("/", 1)
    return svc_attrs[0], svc_category, svc_name, svc_instance


def parse_solaris_services(string_table: StringTable) -> Section:
    parsed: dict[str, SolarisService] = {}
    for line in string_table:
        if len(line) < 3 or line == ["STATE", "STIME", "FMRI"]:
            continue
        svc_descr = line[-1]
        type_, category, name, instance = _get_parts_of_descr(svc_descr)
        parsed.setdefault(
            svc_descr,
            {
                "state": line[0],
                "stime": line[1],
                "type": type_,
                "category": category,
                "name": name,
                "instance": instance,
            },
        )
    return parsed


agent_section_solaris_services = AgentSection(
    name="solaris_services",
    parse_function=parse_solaris_services,
)


#   .--single--------------------------------------------------------------.
#   |                          _             _                             |
#   |                      ___(_)_ __   __ _| | ___                        |
#   |                     / __| | '_ \ / _` | |/ _ \                       |
#   |                     \__ \ | | | | (_| | |  __/                       |
#   |                     |___/_|_| |_|\__, |_|\___|                       |
#   |                                  |___/                               |
#   '----------------------------------------------------------------------'


def _regex_match(what: Collection[str], name: str) -> bool:
    if not what:
        return True
    for entry in what:
        if entry.startswith("~") and re.compile(entry[1:]).match(name):
            return True
        if entry == name:
            return True
    return False


def _state_match(rule_state: str | None, state: str) -> bool:
    if rule_state is not None and rule_state != state:
        return False
    return True


def _get_svc_name(svc_attrs: SolarisService) -> str:
    return "{}/{}:{}".format(svc_attrs["category"], svc_attrs["name"], svc_attrs["instance"])


def discover_solaris_services(
    params: Sequence[Mapping[str, Any]], section: Section
) -> DiscoveryResult:
    for settings in params:
        descriptions = settings.get("descriptions", [])
        categories = settings.get("categories", [])
        names = settings.get("names", [])
        instances = settings.get("instances", [])
        state = settings.get("state")
        for svc_descr, attrs in section.items():
            if (
                _regex_match(descriptions, svc_descr)
                and _regex_match(categories, attrs["category"])
                and _regex_match(names, attrs["name"])
                and _regex_match(instances, attrs["instance"])  # type: ignore[arg-type]  # bug?
                and _state_match(state, attrs["state"])
            ):
                if settings.get("outcome") in [None, "full_descr"]:
                    name = svc_descr
                else:
                    name = _get_svc_name(attrs)
                yield Service(item=name)


def check_solaris_services(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    for svc_name, attrs in section.items():
        if item in svc_name or svc_name in params["additional_servicenames"]:
            svc_state = attrs["state"]
            svc_stime = attrs["stime"]
            if svc_stime.count(":") == 2:
                has_changed = True
                info_stime = "Restarted in the last 24h (client's localtime: %s)" % svc_stime
            else:
                has_changed = False
                info_stime = "Started on %s" % svc_stime.replace("_", " ")

            check_state = 0
            for _, p_stime, p_state in [x for x in params["states"] if x[0] == svc_state]:
                if p_stime is not None:
                    if has_changed == p_stime:
                        check_state = p_state
                        break
                else:
                    check_state = p_state
                    break
            yield Result(
                state=State(check_state),
                summary=f"Status: {svc_state}, {info_stime}",
            )
            return

    yield Result(state=State(params["else"]), summary="Service not found")


check_plugin_solaris_services = CheckPlugin(
    name="solaris_services",
    service_name="SMF Service %s",  # Service Management Facility
    discovery_function=discover_solaris_services,
    discovery_default_parameters=DISCOVER_NOTHING,
    discovery_ruleset_name="inventory_solaris_services_rules",
    discovery_ruleset_type=RuleSetType.ALL,
    check_function=check_solaris_services,
    check_ruleset_name="solaris_services",
    check_default_parameters={
        "states": [
            ("online", None, 0),
            ("disabled", None, 2),
            ("legacy_run", None, 0),
            ("maintenance", None, 0),
        ],
        "else": 2,
        "additional_servicenames": [],
    },
)


# .
#   .--summary-------------------------------------------------------------.
#   |                                                                      |
#   |           ___ _   _ _ __ ___  _ __ ___   __ _ _ __ _   _             |
#   |          / __| | | | '_ ` _ \| '_ ` _ \ / _` | '__| | | |            |
#   |          \__ \ |_| | | | | | | | | | | | (_| | |  | |_| |            |
#   |          |___/\__,_|_| |_| |_|_| |_| |_|\__,_|_|   \__, |            |
#   |                                                    |___/             |
#   '----------------------------------------------------------------------'


def discover_solaris_services_summary(section: Section) -> DiscoveryResult:
    yield Service()


def check_solaris_services_summary(params: Mapping[str, Any], section: Section) -> CheckResult:
    count = len(section)
    yield Result(state=State.OK, summary=f"{count} service{'' if count == 1 else 's'}")

    services_by_state: dict[str, list[str]] = {}
    for svc_name, attrs in section.items():
        services = services_by_state.setdefault(attrs["state"], [])
        services.append(svc_name)

    for svc_state, svc_names in services_by_state.items():
        state = 0
        extra_info = ""
        if svc_state == "maintenance" and params.get("maintenance_state", 0):
            extra_info += " (%s)" % ", ".join(svc_names)
            state = params["maintenance_state"]

        yield Result(
            state=State(state),
            summary="%d %s%s" % (len(svc_names), svc_state.replace("_", " "), extra_info),
        )


check_plugin_solaris_services_summary = CheckPlugin(
    name="solaris_services_summary",
    service_name="SMF Services Summary",  # Service Management Facility
    sections=["solaris_services"],
    discovery_function=discover_solaris_services_summary,
    check_function=check_solaris_services_summary,
    check_default_parameters={},
    check_ruleset_name="solaris_services_summary",
)
