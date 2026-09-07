#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

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


def vbox_guest_make_dict(info: StringTable) -> dict[str, str]:
    # output differs in version 6.x so we need to deal with empty values for
    # /VirtualBox/GuestInfo/OS/ServicePack
    return {l[1].split("/", 2)[2].rstrip(","): l[3] if len(l) == 4 else "" for l in info}


def check_vbox_guest(params: Mapping[str, object], section: StringTable) -> CheckResult:  # noqa: ARG001
    if len(section) == 1 and section[0][0] == "ERROR":
        yield Result(
            state=State.UNKNOWN, summary="Error running VBoxControl guestproperty enumerate"
        )
        return
    try:
        d = vbox_guest_make_dict(section)
    except Exception:
        d = {}

    if len(d) == 0:
        yield Result(state=State.CRIT, summary="No guest additions installed")
        return

    version = d.get("GuestAdd/Version")
    revision = d.get("GuestAdd/Revision")
    if not version or not version[0].isdigit():
        yield Result(state=State.UNKNOWN, summary="No guest addition version available")
        return
    infotext = f"version: {version}, revision: {revision}"

    host_version = d["HostInfo/VBoxVer"]
    host_revision = d["HostInfo/VBoxRev"]
    if (host_version, host_revision) != (version, revision):
        yield Result(
            state=State.WARN, summary=f"{infotext}, Host has {host_version}/{host_revision}"
        )
        return
    yield Result(state=State.OK, summary=infotext)


def discover_vbox_guest(section: StringTable) -> DiscoveryResult:
    if len(section) > 0:
        yield Service()


def parse_vbox_guest(string_table: StringTable) -> StringTable:
    return string_table


agent_section_vbox_guest = AgentSection(
    name="vbox_guest",
    parse_function=parse_vbox_guest,
)

check_plugin_vbox_guest = CheckPlugin(
    name="vbox_guest",
    service_name="VBox Guest Additions",
    discovery_function=discover_vbox_guest,
    check_function=check_vbox_guest,
    check_ruleset_name="vm_state",
    check_default_parameters={},
)
