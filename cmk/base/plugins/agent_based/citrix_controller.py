#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api import v1
from cmk.base.plugins.agent_based.utils.citrix_controller import Error, Section


def discovery_citrix_controller(section: Section) -> v1.type_defs.DiscoveryResult:
    if section.state is not None:
        yield v1.Service()


def check_citrix_controller(section: Section) -> v1.type_defs.CheckResult:
    match section.state:
        case None:
            return
        case Error():
            yield v1.Result(state=v1.State.UNKNOWN, summary="unknown")
        case "Active":
            yield v1.Result(state=v1.State.OK, summary=section.state)
        case _:
            yield v1.Result(state=v1.State.CRIT, summary=section.state)


v1.register.check_plugin(
    name="citrix_controller",
    discovery_function=discovery_citrix_controller,
    check_function=check_citrix_controller,
    service_name="Citrix Controller State",
)


def discovery_citrix_controller_licensing(section: Section) -> v1.type_defs.DiscoveryResult:
    yield v1.Service()


def check_citrix_controller_licensing(section: Section) -> v1.type_defs.CheckResult:
    server_states = {
        "ServerNotSpecified": (v1.State.CRIT, "server not specified"),
        "NotConnected": (v1.State.WARN, "not connected"),
        "OK": (v1.State.OK, "OK"),
        "LicenseNotInstalled": (v1.State.CRIT, "license not installed"),
        "LicenseExpired": (v1.State.CRIT, "licenese expired"),
        "Incompatible": (v1.State.CRIT, "incompatible"),
        "Failed": (v1.State.CRIT, "failed"),
    }
    grace_states = {
        "NotActive": (v1.State.OK, "not active"),
        "Active": (v1.State.CRIT, "active"),
        "InOutOfBoxGracePeriod": (v1.State.WARN, "in-out-of-box grace period"),
        "InSupplementalGracePeriod": (v1.State.WARN, "in-supplemental grace period"),
        "InEmergencyGracePeriod": (v1.State.CRIT, "in-emergency grace period"),
        "GracePeriodExpired": (v1.State.CRIT, "grace period expired"),
        "Expired": (v1.State.CRIT, "expired"),
    }
    if (raw_state := section.licensing_server_state) is not None:
        state, text = server_states.get(raw_state, (v1.State.UNKNOWN, f"unknown[{raw_state}]"))
        yield v1.Result(state=state, summary=f"Licensing Server State: {text}")
    if (raw_state := section.licensing_grace_state) is not None:
        state, text = grace_states.get(raw_state, (v1.State.UNKNOWN, f"unknown[{raw_state}]"))
        yield v1.Result(state=state, summary=f"Licensing Grace State: {text}")


v1.register.check_plugin(
    name="citrix_controller_licensing",
    sections=["citrix_controller"],
    discovery_function=discovery_citrix_controller_licensing,
    check_function=check_citrix_controller_licensing,
    service_name="Citrix Controller Licensing",
)
