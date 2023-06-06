#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing

from cmk.base.plugins.agent_based.agent_based_api import v1
from cmk.base.plugins.agent_based.utils.citrix_controller import Error, Section, Session


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


SERVER_STATES: typing.Final = {
    "ServerNotSpecified": (v1.State.CRIT, "server not specified"),
    "NotConnected": (v1.State.WARN, "not connected"),
    "OK": (v1.State.OK, "OK"),
    "LicenseNotInstalled": (v1.State.CRIT, "license not installed"),
    "LicenseExpired": (v1.State.CRIT, "licenese expired"),
    "Incompatible": (v1.State.CRIT, "incompatible"),
    "Failed": (v1.State.CRIT, "failed"),
}

GRACE_STATES: typing.Final = {
    "NotActive": (v1.State.OK, "not active"),
    "Active": (v1.State.CRIT, "active"),
    "InOutOfBoxGracePeriod": (v1.State.WARN, "in-out-of-box grace period"),
    "InSupplementalGracePeriod": (v1.State.WARN, "in-supplemental grace period"),
    "InEmergencyGracePeriod": (v1.State.CRIT, "in-emergency grace period"),
    "GracePeriodExpired": (v1.State.CRIT, "grace period expired"),
    "Expired": (v1.State.CRIT, "expired"),
}


def check_citrix_controller_licensing(section: Section) -> v1.type_defs.CheckResult:
    if (raw_state := section.licensing_server_state) is not None:
        state, text = SERVER_STATES.get(raw_state, (v1.State.UNKNOWN, f"unknown[{raw_state}]"))
        yield v1.Result(state=state, summary=f"Licensing Server State: {text}")
    if (raw_state := section.licensing_grace_state) is not None:
        state, text = GRACE_STATES.get(raw_state, (v1.State.UNKNOWN, f"unknown[{raw_state}]"))
        yield v1.Result(state=state, summary=f"Licensing Grace State: {text}")


v1.register.check_plugin(
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


def discovery_citrix_controller_sessions(section: Section) -> v1.type_defs.DiscoveryResult:
    if section.session is not None:
        yield v1.Service()


def check_citrix_controller_sessions(
    params: SessionParams, section: Section
) -> v1.type_defs.CheckResult:
    session = Session() if section.session is None else section.session
    yield from v1.check_levels(
        session.active + session.inactive,
        levels_upper=params.get("total"),
        metric_name="total_sessions",
        label="total",
        render_func=str,
    )
    yield from v1.check_levels(
        session.active,
        levels_upper=params.get("active"),
        metric_name="active_sessions",
        label="active",
        render_func=str,
    )
    yield from v1.check_levels(
        session.inactive,
        levels_upper=params.get("inactive"),
        metric_name="inactive_sessions",
        label="inactive",
        render_func=str,
    )


v1.register.check_plugin(
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


def discovery_citrix_controller_registered(section: Section) -> v1.type_defs.DiscoveryResult:
    if section.desktop_count is not None:
        yield v1.Service()


def check_citrix_controller_registered(
    params: DesktopParams, section: Section
) -> v1.type_defs.CheckResult:
    if isinstance(section.desktop_count, Error) or section.desktop_count is None:
        yield v1.Result(state=v1.State.UNKNOWN, summary="No desktops registered")
    else:
        yield from v1.check_levels(
            section.desktop_count,
            metric_name="registered_desktops",
            levels_upper=params.get("levels"),
            levels_lower=params.get("levels_lower"),
            render_func=str,
        )


v1.register.check_plugin(
    name="citrix_controller_registered",
    sections=["citrix_controller"],
    discovery_function=discovery_citrix_controller_registered,
    check_function=check_citrix_controller_registered,
    service_name="Citrix Desktops Registered",
    check_ruleset_name="citrix_desktops_registered",
    check_default_parameters=DesktopParams(),
)


def discovery_citrix_controller_services(section: Section) -> v1.type_defs.DiscoveryResult:
    if section.active_site_services is not None:
        yield v1.Service()


def check_citrix_controller_services(section: Section) -> v1.type_defs.CheckResult:
    if section.active_site_services is not None:
        yield v1.Result(state=v1.State.OK, summary=section.active_site_services or "No services")


v1.register.check_plugin(
    name="citrix_controller_services",
    sections=["citrix_controller"],
    discovery_function=discovery_citrix_controller_services,
    check_function=check_citrix_controller_services,
    service_name="Citrix Active Site Services",
)
