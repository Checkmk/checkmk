#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Result, Service, State
from cmk.plugins.lib.citrix_controller import Error, Section, Session


def discovery_citrix_controller(section: Section) -> DiscoveryResult:
    if section.state is not None:
        yield Service()


def check_citrix_controller(section: Section) -> CheckResult:
    match section.state:
        case None:
            return
        case Error():
            yield Result(state=State.UNKNOWN, summary="unknown")
        case "Active":
            yield Result(state=State.OK, summary=section.state)
        case _:
            yield Result(state=State.CRIT, summary=section.state)


check_plugin_citrix_controller = CheckPlugin(
    name="citrix_controller",
    discovery_function=discovery_citrix_controller,
    check_function=check_citrix_controller,
    service_name="Citrix Controller State",
)


def discovery_citrix_controller_licensing(section: Section) -> DiscoveryResult:
    yield Service()


SERVER_STATES: typing.Final = {
    "ServerNotSpecified": (State.CRIT, "server not specified"),
    "NotConnected": (State.WARN, "not connected"),
    "OK": (State.OK, "OK"),
    "LicenseNotInstalled": (State.CRIT, "license not installed"),
    "LicenseExpired": (State.CRIT, "licenese expired"),
    "Incompatible": (State.CRIT, "incompatible"),
    "Failed": (State.CRIT, "failed"),
}

GRACE_STATES: typing.Final = {
    "NotActive": (State.OK, "not active"),
    "Active": (State.CRIT, "active"),
    "InOutOfBoxGracePeriod": (State.WARN, "in-out-of-box grace period"),
    "InSupplementalGracePeriod": (State.WARN, "in-supplemental grace period"),
    "InEmergencyGracePeriod": (State.CRIT, "in-emergency grace period"),
    "GracePeriodExpired": (State.CRIT, "grace period expired"),
    "Expired": (State.CRIT, "expired"),
}


def check_citrix_controller_licensing(section: Section) -> CheckResult:
    if (raw_state := section.licensing_server_state) is not None:
        state, text = SERVER_STATES.get(raw_state, (State.UNKNOWN, f"unknown[{raw_state}]"))
        yield Result(state=state, summary=f"Licensing Server State: {text}")
    if (raw_state := section.licensing_grace_state) is not None:
        state, text = GRACE_STATES.get(raw_state, (State.UNKNOWN, f"unknown[{raw_state}]"))
        yield Result(state=state, summary=f"Licensing Grace State: {text}")


check_plugin_citrix_controller_licensing = CheckPlugin(
    name="citrix_controller_licensing",
    sections=["citrix_controller"],
    discovery_function=discovery_citrix_controller_licensing,
    check_function=check_citrix_controller_licensing,
    service_name="Citrix Controller Licensing",
)


class SessionParams(typing.TypedDict, total=False):
    total: tuple[int, int]
    active: tuple[int, int]
    inactive: tuple[int, int]


def discovery_citrix_controller_sessions(section: Section) -> DiscoveryResult:
    if section.session is not None:
        yield Service()


def check_citrix_controller_sessions(params: SessionParams, section: Section) -> CheckResult:
    session = Session() if section.session is None else section.session
    yield from check_levels_v1(
        session.active + session.inactive,
        levels_upper=params.get("total"),
        metric_name="total_sessions",
        label="total",
        render_func=str,
    )
    yield from check_levels_v1(
        session.active,
        levels_upper=params.get("active"),
        metric_name="active_sessions",
        label="active",
        render_func=str,
    )
    yield from check_levels_v1(
        session.inactive,
        levels_upper=params.get("inactive"),
        metric_name="inactive_sessions",
        label="inactive",
        render_func=str,
    )


check_plugin_citrix_controller_sessions = CheckPlugin(
    name="citrix_controller_sessions",
    sections=["citrix_controller"],
    discovery_function=discovery_citrix_controller_sessions,
    check_function=check_citrix_controller_sessions,
    service_name="Citrix Total Sessions",
    check_ruleset_name="citrix_sessions",
    check_default_parameters=SessionParams(),
)


class DesktopParams(typing.TypedDict, total=False):
    levels: tuple[int, int]
    levels_lower: tuple[int, int]


def discovery_citrix_controller_registered(section: Section) -> DiscoveryResult:
    if section.desktop_count is not None:
        yield Service()


def check_citrix_controller_registered(params: DesktopParams, section: Section) -> CheckResult:
    if isinstance(section.desktop_count, Error) or section.desktop_count is None:
        yield Result(state=State.UNKNOWN, summary="No desktops registered")
    else:
        yield from check_levels_v1(
            section.desktop_count,
            metric_name="registered_desktops",
            levels_upper=params.get("levels"),
            levels_lower=params.get("levels_lower"),
            render_func=str,
        )


check_plugin_citrix_controller_registered = CheckPlugin(
    name="citrix_controller_registered",
    sections=["citrix_controller"],
    discovery_function=discovery_citrix_controller_registered,
    check_function=check_citrix_controller_registered,
    service_name="Citrix Desktops Registered",
    check_ruleset_name="citrix_desktops_registered",
    check_default_parameters=DesktopParams(),
)


def discovery_citrix_controller_services(section: Section) -> DiscoveryResult:
    if section.active_site_services is not None:
        yield Service()


def check_citrix_controller_services(section: Section) -> CheckResult:
    if section.active_site_services is not None:
        yield Result(state=State.OK, summary=section.active_site_services or "No services")


check_plugin_citrix_controller_services = CheckPlugin(
    name="citrix_controller_services",
    sections=["citrix_controller"],
    discovery_function=discovery_citrix_controller_services,
    check_function=check_citrix_controller_services,
    service_name="Citrix Active Site Services",
)
